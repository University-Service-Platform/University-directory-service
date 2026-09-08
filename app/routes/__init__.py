from app.routes.validation import router as validation_router
from app.routes.health import router as health_router
from app.routes.faculties import router as faculties_router

__all__ = [
    "validation_router",
    "health_router",
    "faculties_router",
]
