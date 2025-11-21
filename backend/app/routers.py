from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app import models
from app import schemas
from app.worker import create_task, super_delete

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
    task = create_task.apply_async(val1,val2)
    
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