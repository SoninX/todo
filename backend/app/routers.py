from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app import models
from app import schemas
from app.worker import create_task, super_delete, process_ocr

import os
from fastapi import UploadFile, File
from fastapi.responses import StreamingResponse
import mimetypes

from app.azure_client import get_blob_service_client, CONTAINER_NAME

router = APIRouter(
    prefix="/todos",
    tags=["Todos"]
)

# 1. CREATE (POST)
@router.post("/", response_model=schemas.TodoResponse, status_code=status.HTTP_201_CREATED)
def create_todo(todo: schemas.TodoCreate, db: Session = Depends(get_db)):
    new_todo = models.Todo(
        title=todo.title,
        description=todo.description,
        completed=todo.completed
    )
    db.add(new_todo)
    db.commit()
    db.refresh(new_todo)
    return new_todo

# 2. READ ALL (GET)
@router.get("/", response_model=List[schemas.TodoResponse])
def read_all_todos(db: Session = Depends(get_db)):
    todos = db.query(models.Todo).all()
    return todos

# 3. READ ONE (GET)
@router.get("/{id}", response_model=schemas.TodoResponse)
def read_todo(id: int, db: Session = Depends(get_db)):
    todo = db.query(models.Todo).filter(models.Todo.id == id).first()
    if not todo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Todo with id {id} not found")
    return todo

# 4. UPDATE (PUT)
@router.put("/{id}", response_model=schemas.TodoResponse)
def update_todo(id: int, todo_update: schemas.TodoUpdate, db: Session = Depends(get_db)):
    todo_query = db.query(models.Todo).filter(models.Todo.id == id)
    todo = todo_query.first()

    if not todo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Todo with id {id} not found")

    # Update only the fields sent by the user
    update_data = todo_update.model_dump(exclude_unset=True)
    todo_query.update(update_data, synchronize_session=False)
    
    db.commit()
    db.refresh(todo)
    return todo

# 5. SUPER DELETE (DELETE)
@router.delete("/super_delete", status_code=status.HTTP_202_ACCEPTED)
def delete_all_todos():
    super_delete.delay()   # send task to celery
    return {"message": "Task received, will be completed shortly"}

# 6. DELETE (DELETE)
@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_todo(id: int, db: Session = Depends(get_db)):
    todo_query = db.query(models.Todo).filter(models.Todo.id == id)
    todo = todo_query.first()

    if not todo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Todo with id {id} not found")

    todo_query.delete(synchronize_session=False)
    db.commit()
    return

@router.post("/background-task", response_model=schemas.TaskDetailResponse)
def run_background_task(val1: int, val2: int, db: Session = Depends(get_db)):
    #create celery task
    task = create_task.apply_async(args = [val1,val2], countdown = 2)
    
    new_task = models.TaskDetail(
        task_id = task.id,
        task_name = "create_task",
        status = "PENDING"
    )
    # when task is created at the same time fill the TaskDetail table with task_id, task_name and put status as pending
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    return new_task

@router.get("/status/{task_id}", response_model=schemas.TaskDetailResponse)
def get_status(task_id: str, db: Session = Depends(get_db)):
    task = db.query(models.TaskDetail).filter(models.TaskDetail.task_id == task_id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"task with id {task_id} not found")
    return task

# --- AZURE UPLOAD / DOWNLOAD ---

@router.post("/Azure_upload")
async def upload_file(file: UploadFile = File(...)):

    try:
        blob_service_client = get_blob_service_client()
        blob_client = blob_service_client.get_blob_client(container=CONTAINER_NAME, blob=file.filename)

        # Upload the file data
        blob_client.upload_blob(file.file.read(), overwrite=True)

        return {"filename": file.filename, "message": "File uploaded successfully to Azure"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/Azure_download/{filename}")
async def download_file(filename: str):

    try:
        blob_service_client = get_blob_service_client()
        blob_client = blob_service_client.get_blob_client(container=CONTAINER_NAME, blob=filename)

        # Check if file exists
        if not blob_client.exists():
            raise HTTPException(status_code=404, detail="File not found in Azure")

        download_stream = blob_client.download_blob()
        
        mime_type, _ = mimetypes.guess_type(filename)
        if not mime_type:
            mime_type = "application/octet-stream"

        return StreamingResponse(download_stream.chunks(), media_type=mime_type, headers={"Content-Disposition": f"attachment; filename={filename}"})

    except Exception as e:
        print(f"Azure Error: {e}") 
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/ocr/analyze")
async def analyze_document(file: UploadFile = File(...), db: Session = Depends(get_db)):
    # 1. Upload to Azure Blob (Reuse your logic)
    try:
        blob_service_client = get_blob_service_client()
        blob_client = blob_service_client.get_blob_client(container=CONTAINER_NAME, blob=file.filename)
        blob_client.upload_blob(file.file.read(), overwrite=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload Failed: {str(e)}")

    # 2. Create DB Entry (Status: PENDING)
    new_doc = models.OCRDocument(
        filename=file.filename,
        status="PENDING"
    )
    db.add(new_doc)
    db.commit()
    db.refresh(new_doc)

    # 3. Trigger Celery Task
    # We pass the filename and the DB ID so the worker knows what to update
    task = process_ocr.apply_async(args=[file.filename, new_doc.id], countdown=2)

    new_task = models.TaskDetail(
        task_id = task.id,
        task_name = "process_ocr",
        status = "PENDING"
    )
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    return {
    "task": new_task,
    "doc_id": new_doc.id
}


@router.get("/ocr/status/{id}")
def get_ocr_status(id: int, db: Session = Depends(get_db)):
    doc = db.query(models.OCRDocument).filter(models.OCRDocument.id == id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc