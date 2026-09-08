from sqlalchemy.orm import Session
from typing import Optional, List
from app.models.faculty import Faculty

class FacultyRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, faculty_id: str) -> Optional[Faculty]:
        return self.db.query(Faculty).filter(Faculty.id == faculty_id).first()

    def get_by_code(self, code: str) -> Optional[Faculty]:
        return self.db.query(Faculty).filter(Faculty.code == code).first()

    def get_by_name(self, name: str) -> Optional[Faculty]:
        return self.db.query(Faculty).filter(Faculty.name == name).first()

    def list_all(self, skip: int = 0, limit: int = 100) -> List[Faculty]:
        return self.db.query(Faculty).offset(skip).limit(limit).all()

    def create(self, faculty: Faculty) -> Faculty:
        self.db.add(faculty)
        self.db.commit()
        self.db.refresh(faculty)
        return faculty

    def update(self, faculty: Faculty) -> Faculty:
        self.db.commit()
        self.db.refresh(faculty)
        return faculty

    def delete(self, faculty: Faculty) -> None:
        self.db.delete(faculty)
        self.db.commit()
