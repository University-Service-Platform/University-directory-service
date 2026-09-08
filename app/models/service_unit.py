from sqlalchemy import Column, String, DateTime
from datetime import datetime
from app.database import Base

class ServiceUnit(Base):
    __tablename__ = "service_units"

    id = Column(String(36), primary_key=True, index=True)
    code = Column(String(20), unique=True, index=True, nullable=False)
    name = Column(String(150), nullable=False)
    description = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
