from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.time import utc_now
from app.database import Base

class Department(Base):
    __tablename__ = "departments"

    id = Column(String(36), primary_key=True, index=True)
    code = Column(String(20), unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False)
    faculty_id = Column(String(36), ForeignKey("faculties.id", ondelete="RESTRICT"), nullable=False)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    faculty = relationship("Faculty", back_populates="departments")
    affiliations = relationship("UserAffiliation", back_populates="department", passive_deletes="all")

