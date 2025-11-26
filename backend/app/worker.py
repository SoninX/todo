import os
import time
from celery import Celery
from sqlalchemy import text # Import text for safe SQL execution
from app.database import SessionLocal
from app import models

from app.azure_client import (
    get_blob_service_client, 
    get_document_analysis_client, 
    CONTAINER_NAME
)

broker_url = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
result_backend = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

celery_app = Celery(
    "worker",
    broker=broker_url,
    backend=result_backend
)
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