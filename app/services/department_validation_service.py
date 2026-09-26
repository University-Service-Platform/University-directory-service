from sqlalchemy.orm import Session
from fastapi import status
from app.core.errors import AppError
from app.schemas.department_validation import DepartmentValidationData
from app.services.lookups import DirectoryLookup

class DepartmentValidationService:
    def __init__(self, db: Session):
        self.lookup = DirectoryLookup(db)

    def validate_department(self, department_id: str) -> DepartmentValidationData:
        dept = self.lookup.department(department_id)

        # Organizational relationship validation
        if not dept.faculty or not dept.faculty_id:
            raise AppError(
                status.HTTP_400_BAD_REQUEST,
                "INVALID_ORGANIZATIONAL_RELATIONSHIP",
                f"Department '{dept.name}' is not associated with a valid Faculty."
            )

        return DepartmentValidationData(
            department_id=dept.id,
            code=dept.code,
            name=dept.name,
            faculty_id=dept.faculty_id,
            faculty_name=dept.faculty.name,
            is_valid=True
        )
