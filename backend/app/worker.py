import os
import time
import json
from celery import Celery
from celery.schedules import crontab
from sqlalchemy import text # Import text for safe SQL execution
from app.database import SessionLocal
from app import models
import openpyxl

from app.azure_client import (
    get_blob_service_client, 
    get_document_analysis_client, 
    get_doc_classified_client,
    CONTAINER_NAME,
    AZURE_OPENAI_DEPLOYMENT_NAME
)

broker_url = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
result_backend = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

celery_app = Celery(
    "worker",
    broker=broker_url,
    backend=result_backend
)
# ---  DEFINE THE SCHEDULE ---
celery_app.conf.beat_schedule = {
    'run-ocr-from-excel-every-morning': {
        'task': 'dispatch_scheduled_ocr',
        'schedule': crontab(hour=15, minute=1),
        # 'schedule': 30.0, ## Run every 30 seconds
    },
}
celery_app.conf.timezone = 'Asia/Kolkata'

def generate_classification_prompt(text_content: str) -> str:
    """Helper to generate the OpenAI prompt"""
    return f"""Please classify the following document text into one of these document types and extract key information:

DOCUMENT TYPES:
- Booking Form - signed or not signed property booking forms
- DEWA (Green Bill) - Dubai Electricity and Water Authority bill  
- Emirates ID - UAE national identity card
- Passport - passport document
- QUOTATION (Quotation Unit) - property quotation document
- SPA (Sales Purchase Agreement) - signed or not signed
- TITLE_DEED - property ownership document
- VISA - visa document

DOCUMENT TEXT:
{text_content}

Respond in JSON format:
{{
    "document_type": "DOCUMENT_TYPE_NAME",
    "confidence": a score for how much you are confident in this classification, ranges from 0-1 or null,
    "reasoning": "Brief explanation",
    "extracted_data": {{
        "Name": "extracted name or null",
        "expiration_date": "YYYY-MM-DD or null"
    }}
}}
"""

# make bind = True so that it can acess self which has task_id
@celery_app.task(bind = True, name="create_task")
def create_task(self, val1, val2):
    #work
    result = val1 + val2
    #give longer seconds to test
    time.sleep(20)
    #after delay time or when process gets over
    # open db session
    db = SessionLocal()
    try:
      task_record = db.query(models.TaskDetail).filter(models.TaskDetail.task_id == self.request.id).first()
      if task_record:
        task_record.status = "COMPLETED"
        db.commit()
    except Exception as e:
        print(f"Error updating task status: {e}")
    finally:
        db.close()
    return {"result": "Task completed", "value": result}

@celery_app.task(name="super_delete")
def super_delete():
    db = SessionLocal()
    try:
        time.sleep(10)
        db.execute(text("TRUNCATE TABLE todos"))
        db.commit()
        time.sleep(3)
        return {"status": "Task Completed"}
    except Exception as e:
        db.rollback()
        return {"status": "Task Failed", "error": str(e)}
    finally:
        db.close()

@celery_app.task(bind=True, name="process_ocr")
def process_ocr(self, filename: str, doc_id: int):
    db = SessionLocal()
    try:
        # 1. Download file
        blob_service = get_blob_service_client()
        blob_client = blob_service.get_blob_client(container=CONTAINER_NAME, blob=filename)
        download_stream = blob_client.download_blob().readall()

        # 2. OCR Analysis
        document_analysis_client = get_document_analysis_client()
        poller = document_analysis_client.begin_analyze_document(
            "prebuilt-read", document=download_stream
        )
        result = poller.result()

        # 3. Extract Text
        full_text = ""
        for page in result.pages:
            for line in page.lines:
                full_text += line.content + "\n"

        # 4. Update OCRDocument (The Business Data)
        ocr_record = db.query(models.OCRDocument).filter(models.OCRDocument.id == doc_id).first()
        if ocr_record:
            ocr_record.extracted_text = full_text
            ocr_record.status = "COMPLETED"

        # 5. Update TaskDetail (The Worker Status)
        # We use self.request.id to find the specific task that is running
        task_record = db.query(models.TaskDetail).filter(models.TaskDetail.task_id == self.request.id).first()
        if task_record:
            task_record.status = "COMPLETED"

        # Commit everything at once
        db.commit()
            
    except Exception as e:
        db.rollback()
        print(f"OCR Failed: {e}")
        
        # Update OCRDocument to FAILED
        ocr_record = db.query(models.OCRDocument).filter(models.OCRDocument.id == doc_id).first()
        if ocr_record:
            ocr_record.status = "FAILED"
            ocr_record.extracted_text = str(e)
            
        # Update TaskDetail to FAILED
        task_record = db.query(models.TaskDetail).filter(models.TaskDetail.task_id == self.request.id).first()
        if task_record:
            task_record.status = "FAILED"
            
        db.commit()
        
    finally:
        db.close()
    
    return "OCR Processing Finished" # add an id

@celery_app.task(name="dispatch_scheduled_ocr")
def dispatch_scheduled_ocr():
    excel_path = "/data/data.xlsx"
    
    if not os.path.exists(excel_path):
        print(f"Excel file not found at {excel_path}")
        return "Excel file missing"

    print(f"Reading Excel file: {excel_path}")
    
    try:
        workbook = openpyxl.load_workbook(excel_path)
        sheet = workbook.active
        
        # Open DB session once
        db = SessionLocal()
        
        try:
            for row in sheet.iter_rows(min_row=1, values_only=True):
                filename = row[0]
                
                if filename:
                    existing_doc = db.query(models.OCRDocument).filter(
                        models.OCRDocument.filename == filename
                    ).first()

                    if existing_doc:
                        print(f"Skipping {filename}: Already exists in DB with status {existing_doc.status}")
                        continue

                    print(f"Found new file: {filename}. Scheduling OCR...")
                    
                    new_doc = models.OCRDocument(
                        filename=filename,
                        status="SCHEDULED"
                    )
                    db.add(new_doc)
                    db.commit()
                    db.refresh(new_doc)
                    
                    # Trigger the worker
                    task = process_ocr.apply_async(args=[filename, new_doc.id], countdown=2)

                    new_task_detail = models.TaskDetail(
                        task_id = task.id,
                        task_name = "process_ocr",
                        status = "SCHEDULED"
                    )
                    db.add(new_task_detail)
                    db.commit()
                    
        finally:
            db.close()
                    
        return "Scheduled processing completed"

    except Exception as e:
        return f"Failed to read Excel: {str(e)}"
    
@celery_app.task(bind=True, name="process_document_ai")
def process_document_ai(self, filename: str, doc_id: int):
    db = SessionLocal()
    try:
        print(f"Starting AI processing for {filename}...")

        blob_service = get_blob_service_client()
        blob_client = blob_service.get_blob_client(container=CONTAINER_NAME, blob=filename)
        download_stream = blob_client.download_blob().readall()

        document_analysis_client = get_document_analysis_client()
        poller = document_analysis_client.begin_analyze_document(
            "prebuilt-read", document=download_stream
        )
        ocr_result = poller.result()

        full_text = ""
        for page in ocr_result.pages:
            for line in page.lines:
                full_text += line.content + "\n"

        formatted_prompt = generate_classification_prompt(full_text[:100000])
        
        openai_client = get_doc_classified_client()
        response = openai_client.chat.completions.create(
            model=AZURE_OPENAI_DEPLOYMENT_NAME,
            messages=[
                {"role": "system", "content": "You are a helpful AI assistant that extracts data from documents."},
                {"role": "user", "content": formatted_prompt}
            ],
            response_format={ "type": "json_object" },
            temperature=0
        )
        
        ai_result_json = response.choices[0].message.content

        doc_record = db.query(models.OCRDocument).filter(models.OCRDocument.id == doc_id).first()
        if doc_record:
            doc_record.extracted_text = full_text
            doc_record.classification_result = ai_result_json
            doc_record.status = "COMPLETED"

        task_record = db.query(models.TaskDetail).filter(models.TaskDetail.task_id == self.request.id).first()
        if task_record:
            task_record.status = "COMPLETED"

        db.commit()
        return "AI Processing Completed"

    except Exception as e:
        db.rollback()
        print(f"AI Processing Failed: {e}")
        
        doc_record = db.query(models.OCRDocument).filter(models.OCRDocument.id == doc_id).first()
        if doc_record:
            doc_record.status = "FAILED"
            doc_record.classification_result = str(e)
            
        task_record = db.query(models.TaskDetail).filter(models.TaskDetail.task_id == self.request.id).first()
        if task_record:
            task_record.status = "FAILED"
            
        db.commit()
    finally:
        db.close()