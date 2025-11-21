from fastapi import FastAPI
import models
from database import engine
import routers as todo_router

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

app.include_router(todo_router.router)