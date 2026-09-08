from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from typing import Optional
from app.database import get_db
from app.services.faculty_validation_service import FacultyValidationService
from app.services.department_validation_service import DepartmentValidationService
from app.services.service_unit_validation_service import ServiceUnitValidationService
from app.services.responsibility_validation_service import ServiceResponsibilityValidationService
from app.schemas.faculty import FacultyValidationResponse
from app.schemas.department_validation import DepartmentValidationResponse
from app.schemas.service_unit_validation import ServiceUnitValidationResponse
from app.schemas.responsibility_validation import UserResponsibilityValidationResponse

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

@router.get(
    "/validation/service-units/{unit_id}",
    response_model=ServiceUnitValidationResponse,
    status_code=status.HTTP_200_OK,
    summary="Validate Service Unit",
    description="Validate Service Unit existence, code, and identifier reference for dependent services."
)
def validate_service_unit(
    unit_id: str,
    db: Session = Depends(get_db)
):
    service = ServiceUnitValidationService(db)
    validation_data = service.validate_service_unit(unit_id=unit_id)
    return ServiceUnitValidationResponse(success=True, data=validation_data)

@router.get(
    "/validation/users/{user_id}/responsibilities",
    response_model=UserResponsibilityValidationResponse,
    status_code=status.HTTP_200_OK,
    summary="Validate Service Responsibility Mappings",
    description="Validate actual service responsibility relationships between a user and organizational units (Service Units, Departments, Faculties)."
)
def validate_user_responsibilities(
    user_id: str,
    service_unit_id: Optional[str] = Query(None, description="Optional filter by Service Unit ID"),
    department_id: Optional[str] = Query(None, description="Optional filter by Department ID"),
    faculty_id: Optional[str] = Query(None, description="Optional filter by Faculty ID"),
    db: Session = Depends(get_db)
):
    service = ServiceResponsibilityValidationService(db)
    validation_data = service.validate_user_responsibilities(
        user_id=user_id,
        service_unit_id=service_unit_id,
        department_id=department_id,
        faculty_id=faculty_id
    )
    return UserResponsibilityValidationResponse(success=True, data=validation_data)
