from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from app.models.department import Department
from app.models.faculty import Faculty
from app.models.service_responsibility import ServiceResponsibility, ResponsibilityStatus
from app.models.service_unit import ServiceUnit
from app.repositories.search import contains_any, normalise_query

class ServiceResponsibilityRepository:
    def __init__(self, db: Session):
        self.db = db

    def _query(self):
        return self.db.query(ServiceResponsibility).options(
            joinedload(ServiceResponsibility.service_unit),
            joinedload(ServiceResponsibility.department),
            joinedload(ServiceResponsibility.faculty)
        )

    def get_by_id(self, responsibility_id: str) -> Optional[ServiceResponsibility]:
        return self._query().filter(ServiceResponsibility.id == responsibility_id).first()

    def get_by_user_id(
        self,
        user_id: str,
        service_unit_id: Optional[str] = None,
        department_id: Optional[str] = None,
        faculty_id: Optional[str] = None
    ) -> List[ServiceResponsibility]:
        query = self._query().filter(ServiceResponsibility.user_id == user_id)

        if service_unit_id:
            query = query.filter(ServiceResponsibility.service_unit_id == service_unit_id)
        if department_id:
            query = query.filter(ServiceResponsibility.department_id == department_id)
        if faculty_id:
            query = query.filter(ServiceResponsibility.faculty_id == faculty_id)

        return query.all()

    def list_all(
        self,
        skip: int = 0,
        limit: int = 100,
        user_id: Optional[str] = None,
        service_unit_id: Optional[str] = None,
        department_id: Optional[str] = None,
        faculty_id: Optional[str] = None,
        status: Optional[ResponsibilityStatus] = None,
        q: Optional[str] = None
    ) -> List[ServiceResponsibility]:
        query = self._query()
        term = normalise_query(q)
        if term:
            query = (
                query.outerjoin(ServiceUnit, ServiceResponsibility.service_unit_id == ServiceUnit.id)
                .outerjoin(Department, ServiceResponsibility.department_id == Department.id)
                .outerjoin(Faculty, ServiceResponsibility.faculty_id == Faculty.id)
                .filter(contains_any(term, ServiceResponsibility.user_id, ServiceResponsibility.role_title,
                                     ServiceUnit.code, ServiceUnit.name, Department.code, Department.name,
                                     Faculty.code, Faculty.name))
            )
        if user_id:
            query = query.filter(ServiceResponsibility.user_id == user_id)
        if service_unit_id:
            query = query.filter(ServiceResponsibility.service_unit_id == service_unit_id)
        if department_id:
            query = query.filter(ServiceResponsibility.department_id == department_id)
        if faculty_id:
            query = query.filter(ServiceResponsibility.faculty_id == faculty_id)
        if status:
            query = query.filter(ServiceResponsibility.status == status)
        return query.order_by(ServiceResponsibility.created_at, ServiceResponsibility.id).offset(skip).limit(limit).all()

    def find_active_duplicate(
        self,
        user_id: str,
        service_unit_id: Optional[str],
        department_id: Optional[str],
        faculty_id: Optional[str],
        exclude_id: Optional[str] = None
    ) -> Optional[ServiceResponsibility]:
        """ACTIVE responsibility for the same user and the same organizational scope (NULL-safe)."""
        query = self.db.query(ServiceResponsibility).filter(
            ServiceResponsibility.user_id == user_id,
            ServiceResponsibility.status == ResponsibilityStatus.ACTIVE,
            ServiceResponsibility.service_unit_id.is_(None) if service_unit_id is None
            else ServiceResponsibility.service_unit_id == service_unit_id,
            ServiceResponsibility.department_id.is_(None) if department_id is None
            else ServiceResponsibility.department_id == department_id,
            ServiceResponsibility.faculty_id.is_(None) if faculty_id is None
            else ServiceResponsibility.faculty_id == faculty_id,
        )
        if exclude_id:
            query = query.filter(ServiceResponsibility.id != exclude_id)
        return query.first()

    def count_referencing(
        self,
        service_unit_id: Optional[str] = None,
        department_id: Optional[str] = None,
        faculty_id: Optional[str] = None
    ) -> int:
        """Count responsibilities (any status) referencing the given unit, department or faculty."""
        query = self.db.query(ServiceResponsibility)
        if service_unit_id:
            query = query.filter(ServiceResponsibility.service_unit_id == service_unit_id)
        if department_id:
            query = query.filter(ServiceResponsibility.department_id == department_id)
        if faculty_id:
            query = query.filter(ServiceResponsibility.faculty_id == faculty_id)
        return query.count()

    def create(self, responsibility: ServiceResponsibility) -> ServiceResponsibility:
        self.db.add(responsibility)
        self.db.commit()
        self.db.refresh(responsibility)
        return responsibility

    def update(self, responsibility: ServiceResponsibility) -> ServiceResponsibility:
        self.db.commit()
        self.db.refresh(responsibility)
        return responsibility

    def delete(self, responsibility: ServiceResponsibility) -> None:
        self.db.delete(responsibility)
        self.db.commit()
