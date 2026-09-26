from fastapi import FastAPI
from app.core.errors import register_exception_handlers
from app.routes.validation import router as validation_router
from app.routes.health import router as health_router
from app.routes.faculties import router as faculties_router
from app.routes.service_units import router as service_units_router
from app.routes.departments import router as departments_router
from app.routes.affiliations import router as affiliations_router
import app.models  # noqa: F401  (register all models)

# The schema is managed by Alembic: run `alembic upgrade head` before starting.

app = FastAPI(
    title="University Directory Service",
    description="Directory microservice handling Faculties, Departments, Service Units, and Responsibilities.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

register_exception_handlers(app)

app.include_router(health_router)
app.include_router(validation_router)
app.include_router(faculties_router)
app.include_router(service_units_router)
app.include_router(departments_router)
app.include_router(affiliations_router)
