from fastapi import APIRouter, status

router = APIRouter(tags=["Health"])

@router.get("/health", status_code=status.HTTP_200_OK)
def health_check():
    return {
        "status": "healthy",
        "service": "directory-service",
        "version": "1.0.0"
    }
