import os
import time
from celery import Celery

broker_url = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
result_backend = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

# 2. Initialize the Celery app with these settings
celery_app = Celery(
    "worker",
    broker=broker_url,
    backend=result_backend
)

# 3. Define the background task
@celery_app.task(name="create_task")
def create_task(task_type):
    # Simulate a heavy process (e.g., processing a file, sending email)
    time.sleep(10) 
    return {"status": "Task completed", "task_type": task_type}