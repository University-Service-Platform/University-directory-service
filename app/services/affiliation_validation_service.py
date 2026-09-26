from sqlalchemy.orm import Session
from fastapi import status
from typing import Optional
from app.core.errors import AppError
from app.core.validators import ensure_identifier
from app.repositories.affiliation_repository import AffiliationRepository
from app.schemas.affiliation_validation import (
    AffiliationMatch,
    OrganizationalUnitRef,
    UserAffiliationValidationData
)
from app.services.lookups import DirectoryLookup, ensure_department_in_faculty

class AffiliationValidationService:
    """Answers "is this user affiliated with this department/faculty?" from directory data only."""

    def __init__(self, db: Session):
        self.repository = AffiliationRepository(db)
        self.lookup = DirectoryLookup(db)

    def validate_user_affiliation(
        self,
        user_id: str,
        department_id: Optional[str] = None,
        faculty_id: Optional[str] = None
    ) -> UserAffiliationValidationData:
        key = ensure_identifier(user_id, "User")
        department = self.lookup.department(department_id) if department_id else None
        faculty = self.lookup.faculty(faculty_id) if faculty_id else None
        if department and faculty:
            ensure_department_in_faculty(department, faculty)

        matches = self.repository.find_for_user(
            user_id=key,
            department_id=department.id if department else None,
            faculty_id=faculty.id if faculty else None
        )
        if not matches:
            raise AppError(
                status.HTTP_404_NOT_FOUND,
                "AFFILIATION_NOT_FOUND",
                f"No affiliation exists for user '{user_id}' matching the requested criteria."
            )

        return UserAffiliationValidationData(
            user_id=key,
            is_valid=True,
            affiliations=[
                AffiliationMatch(
                    affiliation_id=a.id,
                    department=OrganizationalUnitRef(id=a.department.id, code=a.department.code, name=a.department.name),
                    faculty=OrganizationalUnitRef(id=a.faculty.id, code=a.faculty.code, name=a.faculty.name)
                )
                for a in matches
            ]
        )
