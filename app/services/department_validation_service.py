from sqlalchemy.orm import Session
from fastapi import HTTPException, status
import re
from app.repositories.department_repository import DepartmentRepository
from app.schemas.department_validation import DepartmentValidationData

class DepartmentValidationService:
    def __init__(self, db: Session):
        self.repository = DepartmentRepository(db)

    @staticmethod
    def validate_identifier_format(identifier: str) -> bool:
        if not identifier or not isinstance(identifier, str):
            return False
        pattern = r"^[a-zA-Z0-9_-]{2,50}$"
        return bool(re.match(pattern, identifier.strip()))

    def validate_department(self, department_id: str) -> DepartmentValidationData:
        # Step 1: Format check
        if not self.validate_identifier_format(department_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "success": False,
                    "error": {
                        "code": "INVALID_IDENTIFIER_FORMAT",
                        "message": f"Department identifier '{department_id}' has an invalid format."
                    }
                }
            )

        # Step 2: Query department by ID or Code
        dept = self.repository.get_by_id(department_id)
        if not dept:
            dept = self.repository.get_by_code(department_id)

        if not dept:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "success": False,
                    "error": {
                        "code": "DEPARTMENT_NOT_FOUND",
                        "message": f"Department with identifier '{department_id}' was not found."
                    }
                }
            )

        # Step 3: Organizational Relationship Validation
        if not dept.faculty or not dept.faculty_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "success": False,
                    "error": {
                        "code": "INVALID_ORGANIZATIONAL_RELATIONSHIP",
                        "message": f"Department '{dept.name}' is not associated with a valid Faculty."
                    }
                }
            )

        return DepartmentValidationData(
            department_id=dept.id,
            code=dept.code,
            name=dept.name,
            faculty_id=dept.faculty_id,
            faculty_name=dept.faculty.name if dept.faculty else "Unknown",
            is_valid=True
        )
