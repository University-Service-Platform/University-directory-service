from sqlalchemy.orm import Session
from fastapi import status
import uuid
from typing import List, Optional

from app.core.errors import AppError
from app.core.time import utc_now
from app.core.validators import ensure_code
from app.models.department import Department
from app.repositories.affiliation_repository import AffiliationRepository
from app.repositories.department_repository import DepartmentRepository
from app.repositories.responsibility_repository import ServiceResponsibilityRepository
from app.schemas.department import DepartmentCreate, DepartmentUpdate, DepartmentResponse
from app.services.lookups import DirectoryLookup, ensure_no_dependencies

class DepartmentManagementService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = DepartmentRepository(db)
        self.lookup = DirectoryLookup(db)
        self.affiliations = AffiliationRepository(db)
        self.responsibilities = ServiceResponsibilityRepository(db)

    def _to_response(self, department: Department) -> DepartmentResponse:
        return DepartmentResponse(
            id=department.id,
            code=department.code,
            name=department.name,
            faculty_id=department.faculty_id,
            created_at=department.created_at,
            updated_at=department.updated_at
        )

    def _ensure_code_available(self, code: str, current_id: Optional[str] = None) -> None:
        existing = self.repository.get_by_code(code)
        if existing and existing.id != current_id:
            raise AppError(
                status.HTTP_409_CONFLICT,
                "DEPARTMENT_CODE_ALREADY_EXISTS",
                f"Department with code '{code}' already exists."
            )

    def create_department(self, department_in: DepartmentCreate) -> DepartmentResponse:
        normalized_code = department_in.code.strip().upper()
        ensure_code(normalized_code, "Department", display=department_in.code)
        self._ensure_code_available(normalized_code)

        faculty = self.lookup.faculty(department_in.faculty_id)

        new_dept = Department(
            id=f"dept-{normalized_code.lower()}-{uuid.uuid4().hex[:6]}",
            code=normalized_code,
            name=department_in.name.strip(),
            faculty_id=faculty.id,
            created_at=utc_now()
        )

        persisted = self.repository.create(new_dept)
        return self._to_response(persisted)

    def list_departments(
        self,
        skip: int = 0,
        limit: int = 100,
        faculty_id: Optional[str] = None,
        q: Optional[str] = None
    ) -> List[DepartmentResponse]:
        departments = self.repository.list_all(skip=skip, limit=limit, faculty_id=faculty_id, q=q)
        return [self._to_response(d) for d in departments]

    def get_department(self, department_id: str) -> DepartmentResponse:
        return self._to_response(self.lookup.department(department_id))

    def update_department(self, department_id: str, department_update: DepartmentUpdate) -> DepartmentResponse:
        dept = self.lookup.department(department_id)

        if department_update.code is not None:
            new_code = department_update.code.strip().upper()
            ensure_code(new_code, "Department")
            self._ensure_code_available(new_code, current_id=dept.id)
            dept.code = new_code

        if department_update.name is not None:
            dept.name = department_update.name.strip()

        if department_update.faculty_id is not None:
            dept.faculty_id = self.lookup.faculty(department_update.faculty_id).id

        dept.updated_at = utc_now()
        updated = self.repository.update(dept)
        return self._to_response(updated)

    def delete_department(self, department_id: str) -> None:
        dept = self.lookup.department(department_id)
        ensure_no_dependencies(
            "DEPARTMENT_HAS_DEPENDENCIES",
            f"Department '{dept.code}'",
            {
                "affiliation(s)": self.affiliations.count_by_department(dept.id),
                "responsibility(ies)": self.responsibilities.count_referencing(department_id=dept.id),
            },
        )
        self.repository.delete(dept)
