from sqlalchemy.orm import Session
from typing import Optional, List
from app.models.service_unit import ServiceUnit

class ServiceUnitRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, service_unit_id: str) -> Optional[ServiceUnit]:
        return self.db.query(ServiceUnit).filter(ServiceUnit.id == service_unit_id).first()

    def get_by_code(self, code: str) -> Optional[ServiceUnit]:
        return self.db.query(ServiceUnit).filter(ServiceUnit.code == code).first()

    def get_by_name(self, name: str) -> Optional[ServiceUnit]:
        return self.db.query(ServiceUnit).filter(ServiceUnit.name == name).first()

    def list_all(self, skip: int = 0, limit: int = 100) -> List[ServiceUnit]:
        return self.db.query(ServiceUnit).offset(skip).limit(limit).all()

    def create(self, service_unit: ServiceUnit) -> ServiceUnit:
        self.db.add(service_unit)
        self.db.commit()
        self.db.refresh(service_unit)
        return service_unit

    def update(self, service_unit: ServiceUnit) -> ServiceUnit:
        self.db.commit()
        self.db.refresh(service_unit)
        return service_unit

    def delete(self, service_unit: ServiceUnit) -> None:
        self.db.delete(service_unit)
        self.db.commit()
