from sqlalchemy.orm import Session
from fastapi import status
import uuid
from typing import List, Optional

from app.core.errors import AppError
from app.core.time import utc_now
from app.core.validators import ensure_identifier
from app.integrations.identity_client import IdentityClient
from app.models.user_affiliation import UserAffiliation
from app.repositories.affiliation_repository import AffiliationRepository
from app.schemas.affiliation import AffiliationCreate, AffiliationUpdate, AffiliationResponse
from app.services.lookups import DirectoryLookup, ensure_department_in_faculty

class AffiliationManagementService:
    def __init__(self, db: Session, identity_client: Optional[IdentityClient] = None):
        self.db = db
        self.repository = AffiliationRepository(db)
        self.lookup = DirectoryLookup(db)
        self.identity_client = identity_client

    def _ensure_active_user(self, user_id: str) -> str:
        """Identity Service owns users: confirm the user exists and is ACTIVE before writing.

        Returns the canonical Identity user id (the JWT `sub`), which is what gets stored,
        even when the caller supplied a university id.
        """
        if self.identity_client is None:
            raise RuntimeError("AffiliationManagementService needs an IdentityClient for write operations")
        return self.identity_client.get_active_user(user_id).user_id

    def _to_response(self, affiliation: UserAffiliation) -> AffiliationResponse:
        return AffiliationResponse(
            id=affiliation.id,
            user_id=affiliation.user_id,
            department_id=affiliation.department_id,
            department_name=affiliation.department.name if affiliation.department else None,
            department_code=affiliation.department.code if affiliation.department else None,
            faculty_id=affiliation.faculty_id,
            faculty_name=affiliation.faculty.name if affiliation.faculty else None,
            faculty_code=affiliation.faculty.code if affiliation.faculty else None,
            created_at=affiliation.created_at,
            updated_at=affiliation.updated_at
        )

    def _get_affiliation(self, affiliation_id: str) -> UserAffiliation:
        ensure_identifier(affiliation_id, "Affiliation")
        aff = self.repository.get_by_id(affiliation_id)
        if not aff:
            raise AppError(
                status.HTTP_404_NOT_FOUND,
                "AFFILIATION_NOT_FOUND",
                f"Affiliation with identifier '{affiliation_id}' was not found."
            )
        return aff

    def _ensure_not_already_affiliated(self, user_id: str, department, current_id: Optional[str] = None) -> None:
        existing = self.repository.get_by_user_and_department(user_id=user_id, department_id=department.id)
        if existing and existing.id != current_id:
            raise AppError(
                status.HTTP_409_CONFLICT,
                "AFFILIATION_ALREADY_EXISTS",
                f"User '{user_id}' is already affiliated with Department '{department.name}'."
            )

    def create_affiliation(self, affiliation_in: AffiliationCreate) -> AffiliationResponse:
        user_id = self._ensure_active_user(ensure_identifier(affiliation_in.user_id, "User"))
        dept = self.lookup.department(affiliation_in.department_id)

        target_faculty_id = dept.faculty_id
        if affiliation_in.faculty_id:
            faculty = self.lookup.faculty(affiliation_in.faculty_id)
            ensure_department_in_faculty(dept, faculty)
            target_faculty_id = faculty.id

        self._ensure_not_already_affiliated(user_id, dept)

        new_aff = UserAffiliation(
            id=f"aff-{user_id.lower()}-{uuid.uuid4().hex[:6]}",
            user_id=user_id,
            department_id=dept.id,
            faculty_id=target_faculty_id,
            created_at=utc_now()
        )

        persisted = self.repository.create(new_aff)
        return self._to_response(persisted)

    def get_affiliation(self, affiliation_id: str) -> AffiliationResponse:
        return self._to_response(self._get_affiliation(affiliation_id))

    def get_user_affiliation(self, user_id: str) -> AffiliationResponse:
        key = ensure_identifier(user_id, "User")
        aff = self.repository.get_by_user_id(key)
        if not aff:
            raise AppError(
                status.HTTP_404_NOT_FOUND,
                "AFFILIATION_NOT_FOUND",
                f"No organizational affiliation found for user '{user_id}'."
            )
        return self._to_response(aff)

    def list_affiliations(
        self,
        skip: int = 0,
        limit: int = 100,
        department_id: Optional[str] = None,
        faculty_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> List[AffiliationResponse]:
        affiliations = self.repository.list_all(
            skip=skip,
            limit=limit,
            department_id=department_id,
            faculty_id=faculty_id,
            user_id=user_id
        )
        return [self._to_response(a) for a in affiliations]

    def update_affiliation(
        self,
        affiliation_id: str,
        affiliation_update: AffiliationUpdate
    ) -> AffiliationResponse:
        aff = self._get_affiliation(affiliation_id)
        self._ensure_active_user(aff.user_id)

        target_dept = aff.department
        if affiliation_update.department_id is not None:
            target_dept = self.lookup.department(affiliation_update.department_id)

        target_faculty_id = target_dept.faculty_id
        if affiliation_update.faculty_id is not None:
            faculty = self.lookup.faculty(affiliation_update.faculty_id)
            ensure_department_in_faculty(target_dept, faculty)
            target_faculty_id = faculty.id

        if affiliation_update.department_id is not None and target_dept.id != aff.department_id:
            self._ensure_not_already_affiliated(aff.user_id, target_dept, current_id=aff.id)
            aff.department_id = target_dept.id
            aff.faculty_id = target_faculty_id

        aff.updated_at = utc_now()
        updated = self.repository.update(aff)
        return self._to_response(updated)

    def delete_affiliation(self, affiliation_id: str) -> None:
        aff = self._get_affiliation(affiliation_id)
        self.repository.delete(aff)
