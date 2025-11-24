from pydantic import BaseModel
from typing import Optional

class TodoBase(BaseModel):
    title: str
    description: Optional[str] = None
    completed: bool = False
    priority: str

class TodoCreate(TodoBase):
    pass

class TodoUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    completed: Optional[bool] = None
    priority: Optional[str] = None

class TodoResponse(TodoBase):
    id: int

    class Config:
        from_attributes = True

class TaskDetailResponse(BaseModel):
    task_id: str
    task_name: str
    status: str

    class Config:
        from_attributes = True