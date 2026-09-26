from sqlalchemy import Column, String, DateTime
from sqlalchemy.orm import relationship
from app.core.time import utc_now
from app.database import Base

class Faculty(Base):
    __tablename__ = "faculties"

    id = Column(String(36), primary_key=True, index=True)
    code = Column(String(20), unique=True, index=True, nullable=False)
    name = Column(String(150), nullable=False)
    description = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=utc_now)

    departments = relationship("Department", back_populates="faculty", passive_deletes="all")
