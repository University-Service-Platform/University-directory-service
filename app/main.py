from fastapi import Depends, FastAPI
from app.core.errors import register_exception_handlers
from app.core.versioning import API_V1_PREFIX, mark_legacy_route
from app.routes.validation import router as validation_router
from app.routes.health import router as health_router
from app.routes.faculties import router as faculties_router
from app.routes.service_units import router as service_units_router
from app.routes.departments import router as departments_router
from app.routes.affiliations import router as affiliations_router
from app.routes.responsibilities import router as responsibilities_router
import app.models  # noqa: F401  (register all models)

# The schema is managed by Alembic: run `alembic upgrade head` before starting.

app = FastAPI(
    title="University Directory Service",
    description="Directory microservice handling Faculties, Departments, Service Units, "
                "User Affiliations and Service Responsibilities. Versioned API under /api/v1.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

register_exception_handlers(app)

API_V1_ROUTERS = [
    validation_router,
    faculties_router,
    service_units_router,
    departments_router,
    affiliations_router,
    responsibilities_router,
]

# Routers that existed before versioning; their unprefixed paths stay as
# deprecated aliases (hidden from OpenAPI) until dependent services migrate.
LEGACY_ALIAS_ROUTERS = [
    validation_router,
    faculties_router,
    service_units_router,
    departments_router,
    affiliations_router,
]

app.include_router(health_router)

for router in API_V1_ROUTERS:
    app.include_router(router, prefix=API_V1_PREFIX)

for router in LEGACY_ALIAS_ROUTERS:
    app.include_router(
        router,
        include_in_schema=False,
        deprecated=True,
        dependencies=[Depends(mark_legacy_route)],
    )
