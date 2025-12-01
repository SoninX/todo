from sqlalchemy import Column, Integer, String, Boolean, Text
from app.database import Base

class Todo(Base):
    __tablename__ = "todos"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(String, nullable=True)
    completed = Column(Boolean, default=False)
    priority = Column(String, default="LOW")

class TaskDetail(Base):
    __tablename__ = "task_detail"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String, unique=True, index=True)
    task_name = Column(String)
    status = Column(String, default="PENDING")

class OCRDocument(Base):
    __tablename__ = "ocr_documents"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String)
    status = Column(String, default="PENDING")
    extracted_text = Column(Text, nullable=True)
    classification_result = Column(Text, nullable=True)