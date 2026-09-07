from sqlalchemy.orm import Session
from fastapi import HTTPException, status
import re
from app.repositories.faculty_repository import FacultyRepository
from app.schemas.faculty import FacultyValidationData

class FacultyValidationService:
    def __init__(self, db: Session):
        self.repository = FacultyRepository(db)

    @staticmethod
    def validate_identifier_format(faculty_id: str) -> bool:
        if not faculty_id or not isinstance(faculty_id, str):
            return False
        pattern = r"^[a-zA-Z0-9_-]{2,50}$"
        return bool(re.match(pattern, faculty_id.strip()))

    def validate_faculty(self, faculty_id: str) -> FacultyValidationData:
        # Step 1: Validate identifier format
        if not self.validate_identifier_format(faculty_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "success": False,
                    "error": {
                        "code": "INVALID_IDENTIFIER_FORMAT",
                        "message": f"Faculty identifier '{faculty_id}' has an invalid format."
                    }
                }
            )

        # Step 2: Query by ID or Faculty Code
        faculty = self.repository.get_by_id(faculty_id)
        if not faculty:
            faculty = self.repository.get_by_code(faculty_id)

        if not faculty:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "success": False,
                    "error": {
                        "code": "FACULTY_NOT_FOUND",
                        "message": f"Faculty with identifier '{faculty_id}' was not found."
                    }
                }
            )

        return FacultyValidationData(
            faculty_id=faculty.id,
            code=faculty.code,
            name=faculty.name,
            is_valid=True
        )
