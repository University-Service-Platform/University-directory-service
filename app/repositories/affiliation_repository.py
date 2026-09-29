from sqlalchemy.orm import Session, joinedload
from typing import Optional, List
from app.models.department import Department
from app.models.faculty import Faculty
from app.models.user_affiliation import UserAffiliation
from app.repositories.search import contains_any, normalise_query

class AffiliationRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, affiliation_id: str) -> Optional[UserAffiliation]:
        return (
            self.db.query(UserAffiliation)
            .options(
                joinedload(UserAffiliation.department),
                joinedload(UserAffiliation.faculty)
            )
            .filter(UserAffiliation.id == affiliation_id)
            .first()
        )

    def get_by_user_id(self, user_id: str) -> Optional[UserAffiliation]:
        return (
            self.db.query(UserAffiliation)
            .options(
                joinedload(UserAffiliation.department),
                joinedload(UserAffiliation.faculty)
            )
            .filter(UserAffiliation.user_id == user_id)
            .first()
        )

    def get_by_user_and_department(self, user_id: str, department_id: str) -> Optional[UserAffiliation]:
        return (
            self.db.query(UserAffiliation)
            .options(
                joinedload(UserAffiliation.department),
                joinedload(UserAffiliation.faculty)
            )
            .filter(
                UserAffiliation.user_id == user_id,
                UserAffiliation.department_id == department_id
            )
            .first()
        )

    def list_all(
        self,
        skip: int = 0,
        limit: int = 100,
        department_id: Optional[str] = None,
        faculty_id: Optional[str] = None,
        user_id: Optional[str] = None,
        q: Optional[str] = None
    ) -> List[UserAffiliation]:
        query = (
            self.db.query(UserAffiliation)
            .options(
                joinedload(UserAffiliation.department),
                joinedload(UserAffiliation.faculty)
            )
        )
        if department_id:
            query = query.filter(UserAffiliation.department_id == department_id)
        if faculty_id:
            query = query.filter(UserAffiliation.faculty_id == faculty_id)
        if user_id:
            query = query.filter(UserAffiliation.user_id == user_id)
        term = normalise_query(q)
        if term:
            query = (
                query.join(Department, UserAffiliation.department_id == Department.id)
                .join(Faculty, UserAffiliation.faculty_id == Faculty.id)
                .filter(contains_any(term, UserAffiliation.user_id, Department.code, Department.name,
                                     Faculty.code, Faculty.name))
            )

        return query.order_by(UserAffiliation.created_at, UserAffiliation.id).offset(skip).limit(limit).all()

    def find_for_user(
        self,
        user_id: str,
        department_id: Optional[str] = None,
        faculty_id: Optional[str] = None
    ) -> List[UserAffiliation]:
        query = (
            self.db.query(UserAffiliation)
            .options(
                joinedload(UserAffiliation.department),
                joinedload(UserAffiliation.faculty)
            )
            .filter(UserAffiliation.user_id == user_id)
        )
        if department_id:
            query = query.filter(UserAffiliation.department_id == department_id)
        if faculty_id:
            query = query.filter(UserAffiliation.faculty_id == faculty_id)
        return query.order_by(UserAffiliation.created_at, UserAffiliation.id).all()

    def count_by_department(self, department_id: str) -> int:
        return self.db.query(UserAffiliation).filter(UserAffiliation.department_id == department_id).count()

    def count_by_faculty(self, faculty_id: str) -> int:
        return self.db.query(UserAffiliation).filter(UserAffiliation.faculty_id == faculty_id).count()

    def create(self, affiliation: UserAffiliation) -> UserAffiliation:
        self.db.add(affiliation)
        self.db.commit()
        self.db.refresh(affiliation)
        return affiliation

    def update(self, affiliation: UserAffiliation) -> UserAffiliation:
        self.db.commit()
        self.db.refresh(affiliation)
        return affiliation

    def delete(self, affiliation: UserAffiliation) -> None:
        self.db.delete(affiliation)
        self.db.commit()
