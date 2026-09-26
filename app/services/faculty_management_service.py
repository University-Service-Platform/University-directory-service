from sqlalchemy.orm import Session
from fastapi import status
import uuid
from typing import List, Optional

from app.core.errors import AppError
from app.core.time import utc_now
from app.core.validators import ensure_code
from app.models.faculty import Faculty
from app.repositories.faculty_repository import FacultyRepository
from app.schemas.faculty import FacultyCreate, FacultyUpdate, FacultyResponse
from app.services.lookups import DirectoryLookup

class FacultyManagementService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = FacultyRepository(db)
        self.lookup = DirectoryLookup(db)

    def _to_response(self, faculty: Faculty) -> FacultyResponse:
        return FacultyResponse(
            id=faculty.id,
            code=faculty.code,
            name=faculty.name,
            description=faculty.description,
            created_at=faculty.created_at
        )

    def _ensure_code_available(self, code: str, current_id: Optional[str] = None) -> None:
        existing = self.repository.get_by_code(code)
        if existing and existing.id != current_id:
            raise AppError(
                status.HTTP_409_CONFLICT,
                "FACULTY_CODE_ALREADY_EXISTS",
                f"Faculty with code '{code}' already exists."
            )

    def create_faculty(self, faculty_in: FacultyCreate) -> FacultyResponse:
        normalized_code = faculty_in.code.strip().upper()
        ensure_code(normalized_code, "Faculty", display=faculty_in.code)
        self._ensure_code_available(normalized_code)

        new_faculty = Faculty(
            id=f"fac-{normalized_code.lower()}-{uuid.uuid4().hex[:6]}",
            code=normalized_code,
            name=faculty_in.name.strip(),
            description=faculty_in.description.strip() if faculty_in.description else None,
            created_at=utc_now()
        )

        persisted = self.repository.create(new_faculty)
        return self._to_response(persisted)

    def list_faculties(self, skip: int = 0, limit: int = 100) -> List[FacultyResponse]:
        faculties = self.repository.list_all(skip=skip, limit=limit)
        return [self._to_response(f) for f in faculties]

    def get_faculty(self, faculty_id: str) -> FacultyResponse:
        return self._to_response(self.lookup.faculty(faculty_id))

    def update_faculty(self, faculty_id: str, faculty_update: FacultyUpdate) -> FacultyResponse:
        faculty = self.lookup.faculty(faculty_id)

        if faculty_update.code is not None:
            new_code = faculty_update.code.strip().upper()
            ensure_code(new_code, "Faculty")
            self._ensure_code_available(new_code, current_id=faculty.id)
            faculty.code = new_code

        if faculty_update.name is not None:
            faculty.name = faculty_update.name.strip()

        if faculty_update.description is not None:
            faculty.description = faculty_update.description.strip()

        updated = self.repository.update(faculty)
        return self._to_response(updated)

    def delete_faculty(self, faculty_id: str) -> None:
        faculty = self.lookup.faculty(faculty_id)
        self.repository.delete(faculty)
