from sqlalchemy.orm import Session, joinedload
from typing import Optional
from app.models.department import Department

class DepartmentRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, department_id: str) -> Optional[Department]:
        return (
            self.db.query(Department)
            .options(joinedload(Department.faculty))
            .filter(Department.id == department_id)
            .first()
        )

    def get_by_code(self, code: str) -> Optional[Department]:
        return (
            self.db.query(Department)
            .options(joinedload(Department.faculty))
            .filter(Department.code == code.upper())
            .first()
        )
