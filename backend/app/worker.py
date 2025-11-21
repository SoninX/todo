import os
import time
from celery import Celery
from sqlalchemy import text # Import text for safe SQL execution
from app.database import SessionLocal
from app import models

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