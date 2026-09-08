from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from app.models.service_responsibility import ServiceResponsibility, ResponsibilityStatus

class ServiceResponsibilityRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_user_id(
        self,
        user_id: str,
        service_unit_id: Optional[str] = None,
        department_id: Optional[str] = None,
        faculty_id: Optional[str] = None
    ) -> List[ServiceResponsibility]:
        query = (
            self.db.query(ServiceResponsibility)
            .options(
                joinedload(ServiceResponsibility.service_unit),
                joinedload(ServiceResponsibility.department),
                joinedload(ServiceResponsibility.faculty)
            )
            .filter(ServiceResponsibility.user_id == user_id)
        )

        if service_unit_id:
            query = query.filter(ServiceResponsibility.service_unit_id == service_unit_id)
        if department_id:
            query = query.filter(ServiceResponsibility.department_id == department_id)
        if faculty_id:
            query = query.filter(ServiceResponsibility.faculty_id == faculty_id)

        return query.all()
