from fastapi import FastAPI
from app.routes.health import router as health_router

app = FastAPI(
    title="University Directory Service",
    description="Directory microservice handling Faculties, Departments, Service Units, and Responsibilities.",
    version="1.0.0",
    docs_url="/docs"
)

app.include_router(health_router)
