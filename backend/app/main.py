from fastapi import FastAPI
from app import models
from app.database import engine
from app import routers as todo_router

#models.Base.metadata.create_all(bind=engine)

app = FastAPI()

app.include_router(todo_router.router)