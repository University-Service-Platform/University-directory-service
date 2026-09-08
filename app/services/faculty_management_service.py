from sqlalchemy.orm import Session
from fastapi import HTTPException, status
import uuid
import re
from typing import List
from datetime import datetime

from app.models.faculty import Faculty
from app.repositories.faculty_repository import FacultyRepository
from app.schemas.faculty import FacultyCreate, FacultyUpdate, FacultyResponse

class FacultyManagementService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = FacultyRepository(db)

    @staticmethod
    def validate_code_format(code: str) -> bool:
        if not code or not isinstance(code, str):
            return False
        pattern = r"^[a-zA-Z0-9_-]{2,20}$"
        return bool(re.match(pattern, code.strip()))

    @staticmethod
    def validate_identifier_format(faculty_id: str) -> bool:
        if not faculty_id or not isinstance(faculty_id, str):
            return False
        pattern = r"^[a-zA-Z0-9_-]{2,50}$"
        return bool(re.match(pattern, faculty_id.strip()))

    def _to_response(self, faculty: Faculty) -> FacultyResponse:
        return FacultyResponse(
            id=faculty.id,
            code=faculty.code,
            name=faculty.name,
            description=faculty.description,
            created_at=faculty.created_at
        )

    def create_faculty(self, faculty_in: FacultyCreate) -> FacultyResponse:
        normalized_code = faculty_in.code.strip().upper()
        if not self.validate_code_format(normalized_code):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "success": False,
                    "error": {
                        "code": "INVALID_IDENTIFIER_FORMAT",
                        "message": f"Faculty code '{faculty_in.code}' has an invalid format."
                    }
                }
            )

        # Check duplicate code
        if self.repository.get_by_code(normalized_code):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "success": False,
                    "error": {
                        "code": "FACULTY_CODE_ALREADY_EXISTS",
                        "message": f"Faculty with code '{normalized_code}' already exists."
                    }
                }
            )

        new_faculty = Faculty(
            id=f"fac-{normalized_code.lower()}-{uuid.uuid4().hex[:6]}",
            code=normalized_code,
            name=faculty_in.name.strip(),
            description=faculty_in.description.strip() if faculty_in.description else None,
            created_at=datetime.utcnow()
        )

        persisted = self.repository.create(new_faculty)
        return self._to_response(persisted)

    def list_faculties(self, skip: int = 0, limit: int = 100) -> List[FacultyResponse]:
        faculties = self.repository.list_all(skip=skip, limit=limit)
        return [self._to_response(f) for f in faculties]

    def get_faculty(self, faculty_id: str) -> FacultyResponse:
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

        faculty = self.repository.get_by_id(faculty_id)
        if not faculty:
            faculty = self.repository.get_by_code(faculty_id.strip().upper())

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

        return self._to_response(faculty)

    def update_faculty(self, faculty_id: str, faculty_update: FacultyUpdate) -> FacultyResponse:
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

        faculty = self.repository.get_by_id(faculty_id)
        if not faculty:
            faculty = self.repository.get_by_code(faculty_id.strip().upper())

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

        if faculty_update.code is not None:
            new_code = faculty_update.code.strip().upper()
            if not self.validate_code_format(new_code):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "success": False,
                        "error": {
                            "code": "INVALID_IDENTIFIER_FORMAT",
                            "message": f"Faculty code '{new_code}' has an invalid format."
                        }
                    }
                )
            existing = self.repository.get_by_code(new_code)
            if existing and existing.id != faculty.id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "success": False,
                        "error": {
                            "code": "FACULTY_CODE_ALREADY_EXISTS",
                            "message": f"Faculty with code '{new_code}' already exists."
                        }
                    }
                )
            faculty.code = new_code

        if faculty_update.name is not None:
            faculty.name = faculty_update.name.strip()

        if faculty_update.description is not None:
            faculty.description = faculty_update.description.strip()

        updated = self.repository.update(faculty)
        return self._to_response(updated)

    def delete_faculty(self, faculty_id: str) -> None:
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

        faculty = self.repository.get_by_id(faculty_id)
        if not faculty:
            faculty = self.repository.get_by_code(faculty_id.strip().upper())

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

        self.repository.delete(faculty)
