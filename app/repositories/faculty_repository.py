from sqlalchemy.orm import Session
from typing import Optional
from app.models.faculty import Faculty

class FacultyRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, faculty_id: str) -> Optional[Faculty]:
        return self.db.query(Faculty).filter(Faculty.id == faculty_id).first()

    def get_by_code(self, code: str) -> Optional[Faculty]:
        return self.db.query(Faculty).filter(Faculty.code == code).first()
