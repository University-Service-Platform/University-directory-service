from sqlalchemy.orm import Session
from app.schemas.faculty import FacultyValidationData
from app.services.lookups import DirectoryLookup

class FacultyValidationService:
    def __init__(self, db: Session):
        self.lookup = DirectoryLookup(db)

    def validate_faculty(self, faculty_id: str) -> FacultyValidationData:
        faculty = self.lookup.faculty(faculty_id)
        return FacultyValidationData(
            faculty_id=faculty.id,
            code=faculty.code,
            name=faculty.name,
            is_valid=True
        )
