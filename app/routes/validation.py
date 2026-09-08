from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.faculty_validation_service import FacultyValidationService
from app.services.department_validation_service import DepartmentValidationService
from app.schemas.faculty import FacultyValidationResponse
from app.schemas.department_validation import DepartmentValidationResponse

router = APIRouter(tags=["Directory Validation"])

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

@router.get(
    "/validation/departments/{department_id}",
    response_model=DepartmentValidationResponse,
    status_code=status.HTTP_200_OK,
    summary="Validate Department",
    description="Validate Department existence, identifier/code, and parent Faculty relationship for dependent services."
)
def validate_department(
    department_id: str,
    db: Session = Depends(get_db)
):
    service = DepartmentValidationService(db)
    validation_data = service.validate_department(department_id=department_id)
    return DepartmentValidationResponse(success=True, data=validation_data)
