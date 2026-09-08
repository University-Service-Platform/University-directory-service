from sqlalchemy import Column, String, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.database import Base

class ResponsibilityStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"

class ServiceResponsibility(Base):
    __tablename__ = "service_responsibilities"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), index=True, nullable=False)
    service_unit_id = Column(String(36), ForeignKey("service_units.id", ondelete="CASCADE"), nullable=True)
    department_id = Column(String(36), ForeignKey("departments.id", ondelete="CASCADE"), nullable=True)
    faculty_id = Column(String(36), ForeignKey("faculties.id", ondelete="CASCADE"), nullable=True)
    role_title = Column(String(100), nullable=False)
    status = Column(SQLEnum(ResponsibilityStatus), default=ResponsibilityStatus.ACTIVE, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    service_unit = relationship("ServiceUnit")
    department = relationship("Department")
    faculty = relationship("Faculty")
