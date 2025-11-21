from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app import models
from app import schemas

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

# 5. DELETE (DELETE)
@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_todo(id: int, db: Session = Depends(get_db)):
    todo_query = db.query(models.Todo).filter(models.Todo.id == id)
    todo = todo_query.first()

    if not todo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Todo with id {id} not found")

    todo_query.delete(synchronize_session=False)
    db.commit()
    return