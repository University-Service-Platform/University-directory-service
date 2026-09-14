from sqlalchemy.orm import Session, joinedload
from typing import Optional, List
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

    def get_by_name(self, name: str) -> Optional[Department]:
        return (
            self.db.query(Department)
            .options(joinedload(Department.faculty))
            .filter(Department.name == name)
            .first()
        )

    def list_all(self, skip: int = 0, limit: int = 100, faculty_id: Optional[str] = None) -> List[Department]:
        query = self.db.query(Department).options(joinedload(Department.faculty))
        if faculty_id:
            query = query.filter(Department.faculty_id == faculty_id)
        return query.offset(skip).limit(limit).all()

    def create(self, department: Department) -> Department:
        self.db.add(department)
        self.db.commit()
        self.db.refresh(department)
        return department

    def update(self, department: Department) -> Department:
        self.db.commit()
        self.db.refresh(department)
        return department

    def delete(self, department: Department) -> None:
        self.db.delete(department)
        self.db.commit()

