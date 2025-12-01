from pydantic import BaseModel, Json
from typing import Optional, Any

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

class OCRDocumentResponse(BaseModel):
    id: int
    filename: str
    status: str
    extracted_text: Optional[str] = None
    classification_result: Optional[Json] = None 

    class Config:
        from_attributes = True

# Schema for the Upload Response (so you get the IDs back)
class ClassificationJobResponse(BaseModel):
    message: str
    doc_id: int
    task_id: str