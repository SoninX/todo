import os
import time
from celery import Celery
from app.database import SessionLocal
from app import models

broker_url = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
result_backend = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

celery_app = Celery(
    "worker",
    broker=broker_url,
    backend=result_backend
)

@celery_app.task(name="create_task")
def create_task(val1,val2):
    result = val1 + val2
    time.sleep(10) 
    return {"result": "Task completed", "value": result}

@celery_app.task(name="super_delete")
def super_delete():
    db=SessionLocal()
    try:
        db.execute("TRUNCATE TABLE todo")
        db.commit()
        time.sleep(3)
        return {"Task Completed"}
    finally:
        db.close()