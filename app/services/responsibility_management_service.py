from sqlalchemy.orm import Session
from fastapi import status
import uuid
from typing import List, Optional

from app.core.errors import AppError
from app.core.time import utc_now
from app.core.validators import ensure_identifier
from app.integrations.identity_client import IdentityClient
from app.models.service_responsibility import ResponsibilityStatus, ServiceResponsibility
from app.repositories.responsibility_repository import ServiceResponsibilityRepository
from app.schemas.responsibility import ResponsibilityCreate, ResponsibilityUpdate, ResponsibilityResponse
from app.services.lookups import DirectoryLookup, ensure_department_in_faculty

class ResponsibilityManagementService:
    def __init__(self, db: Session, identity_client: Optional[IdentityClient] = None):
        self.db = db
        self.repository = ServiceResponsibilityRepository(db)
        self.lookup = DirectoryLookup(db)
        self.identity_client = identity_client

    def _to_response(self, r: ServiceResponsibility) -> ResponsibilityResponse:
        return ResponsibilityResponse(
            id=r.id,
            user_id=r.user_id,
            service_unit_id=r.service_unit_id,
            service_unit_code=r.service_unit.code if r.service_unit else None,
            service_unit_name=r.service_unit.name if r.service_unit else None,
            department_id=r.department_id,
            department_code=r.department.code if r.department else None,
            department_name=r.department.name if r.department else None,
            faculty_id=r.faculty_id,
            faculty_code=r.faculty.code if r.faculty else None,
            faculty_name=r.faculty.name if r.faculty else None,
            role_title=r.role_title,
            status=r.status,
            created_at=r.created_at,
            updated_at=r.updated_at
        )

    def _get_responsibility(self, responsibility_id: str) -> ServiceResponsibility:
        ensure_identifier(responsibility_id, "Responsibility")
        responsibility = self.repository.get_by_id(responsibility_id.strip())
        if not responsibility:
            raise AppError(
                status.HTTP_404_NOT_FOUND,
                "RESPONSIBILITY_NOT_FOUND",
                f"Responsibility with identifier '{responsibility_id}' was not found."
            )
        return responsibility

    def _identity(self) -> IdentityClient:
        if self.identity_client is None:
            raise RuntimeError("ResponsibilityManagementService needs an IdentityClient for write operations")
        return self.identity_client

    def _resolve_user(self, user_id: str, require_active: bool) -> str:
        """Identity Service owns users: the user must exist (and be ACTIVE for an ACTIVE responsibility).

        Returns the canonical Identity user id (the JWT `sub`), which is what gets stored.
        """
        if require_active:
            return self._identity().get_active_user(user_id).user_id
        return self._identity().lookup_user(user_id).user_id

    def _resolve_scope(
        self,
        service_unit_id: Optional[str],
        department_id: Optional[str],
        faculty_id: Optional[str]
    ):
        """Resolve identifiers or codes to canonical ids; department must belong to faculty if both are set."""
        unit = self.lookup.service_unit(service_unit_id) if service_unit_id else None
        department = self.lookup.department(department_id) if department_id else None
        faculty = self.lookup.faculty(faculty_id) if faculty_id else None
        if department and faculty:
            ensure_department_in_faculty(department, faculty)
        return (
            unit.id if unit else None,
            department.id if department else None,
            faculty.id if faculty else None,
        )

    def _ensure_no_active_duplicate(self, user_id, unit_id, department_id, faculty_id, exclude_id=None) -> None:
        if self.repository.find_active_duplicate(user_id, unit_id, department_id, faculty_id, exclude_id):
            raise AppError(
                status.HTTP_409_CONFLICT,
                "RESPONSIBILITY_ALREADY_EXISTS",
                f"User '{user_id}' already has an active responsibility for this organizational unit."
            )

    def create_responsibility(self, data: ResponsibilityCreate) -> ResponsibilityResponse:
        requested_user_id = ensure_identifier(data.user_id, "User")
        unit_id, department_id, faculty_id = self._resolve_scope(
            data.service_unit_id, data.department_id, data.faculty_id
        )
        is_active = data.status == ResponsibilityStatus.ACTIVE
        user_id = self._resolve_user(requested_user_id, require_active=is_active)

        if is_active:
            self._ensure_no_active_duplicate(user_id, unit_id, department_id, faculty_id)

        now = utc_now()
        responsibility = ServiceResponsibility(
            id=f"resp-{uuid.uuid4().hex[:12]}",
            user_id=user_id,
            service_unit_id=unit_id,
            department_id=department_id,
            faculty_id=faculty_id,
            role_title=data.role_title.strip(),
            status=data.status,
            created_at=now,
            updated_at=now
        )
        return self._to_response(self.repository.create(responsibility))

    def get_responsibility(self, responsibility_id: str) -> ResponsibilityResponse:
        return self._to_response(self._get_responsibility(responsibility_id))

    def list_responsibilities(
        self,
        skip: int = 0,
        limit: int = 100,
        user_id: Optional[str] = None,
        service_unit_id: Optional[str] = None,
        department_id: Optional[str] = None,
        faculty_id: Optional[str] = None,
        status_filter: Optional[ResponsibilityStatus] = None,
        q: Optional[str] = None
    ) -> List[ResponsibilityResponse]:
        records = self.repository.list_all(
            skip=skip,
            limit=limit,
            user_id=user_id,
            service_unit_id=service_unit_id,
            department_id=department_id,
            faculty_id=faculty_id,
            status=status_filter,
            q=q
        )
        return [self._to_response(r) for r in records]

    def update_responsibility(self, responsibility_id: str, data: ResponsibilityUpdate) -> ResponsibilityResponse:
        responsibility = self._get_responsibility(responsibility_id)

        unit_id, department_id, faculty_id = self._resolve_scope(
            data.service_unit_id if data.service_unit_id is not None else responsibility.service_unit_id,
            data.department_id if data.department_id is not None else responsibility.department_id,
            data.faculty_id if data.faculty_id is not None else responsibility.faculty_id,
        )
        new_status = data.status if data.status is not None else responsibility.status

        if new_status == ResponsibilityStatus.ACTIVE:
            self._ensure_no_active_duplicate(
                responsibility.user_id, unit_id, department_id, faculty_id, exclude_id=responsibility.id
            )
            self._resolve_user(responsibility.user_id, require_active=True)

        responsibility.service_unit_id = unit_id
        responsibility.department_id = department_id
        responsibility.faculty_id = faculty_id
        responsibility.status = new_status
        if data.role_title is not None:
            responsibility.role_title = data.role_title.strip()
        responsibility.updated_at = utc_now()

        return self._to_response(self.repository.update(responsibility))

    def delete_responsibility(self, responsibility_id: str) -> None:
        self.repository.delete(self._get_responsibility(responsibility_id))
