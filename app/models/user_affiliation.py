from sqlalchemy import Column, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.core.time import utc_now
from app.database import Base

class UserAffiliation(Base):
    __tablename__ = "user_affiliations"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(50), index=True, nullable=False)
    department_id = Column(String(36), ForeignKey("departments.id", ondelete="CASCADE"), nullable=False)
    faculty_id = Column(String(36), ForeignKey("faculties.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    department = relationship("Department", back_populates="affiliations")
    faculty = relationship("Faculty")


    __table_args__ = (
        UniqueConstraint("user_id", "department_id", name="uq_user_department_affiliation"),
    )
