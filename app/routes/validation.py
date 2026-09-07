from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.faculty_validation_service import FacultyValidationService
from app.schemas.faculty import FacultyValidationResponse

router = APIRouter(tags=["Faculty Validation"])

@router.get(
    "/validation/faculties/{faculty_id}",
    response_model=FacultyValidationResponse,
    status_code=status.HTTP_200_OK,
    summary="Validate Faculty",
    description="Validate Faculty existence, code, and identifier reference for dependent services."
)
def validate_faculty(
    faculty_id: str,
    db: Session = Depends(get_db)
):
    service = FacultyValidationService(db)
    validation_data = service.validate_faculty(faculty_id=faculty_id)
    return FacultyValidationResponse(success=True, data=validation_data)
