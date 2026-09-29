from sqlalchemy.orm import Session
from app.schemas.service_unit_validation import ServiceUnitValidationData
from app.services.lookups import DirectoryLookup

class ServiceUnitValidationService:
    def __init__(self, db: Session):
        self.lookup = DirectoryLookup(db)

    def validate_service_unit(self, unit_id: str) -> ServiceUnitValidationData:
        unit = self.lookup.service_unit(unit_id)
        return ServiceUnitValidationData(
            unit_id=unit.id,
            code=unit.code,
            name=unit.name,
            description=unit.description,
            is_valid=True
        )
