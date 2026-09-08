from sqlalchemy.orm import Session
from fastapi import HTTPException, status
import re
from app.repositories.service_unit_repository import ServiceUnitRepository
from app.schemas.service_unit_validation import ServiceUnitValidationData

class ServiceUnitValidationService:
    def __init__(self, db: Session):
        self.repository = ServiceUnitRepository(db)

    @staticmethod
    def validate_identifier_format(identifier: str) -> bool:
        if not identifier or not isinstance(identifier, str):
            return False
        pattern = r"^[a-zA-Z0-9_-]{2,50}$"
        return bool(re.match(pattern, identifier.strip()))

    def validate_service_unit(self, unit_id: str) -> ServiceUnitValidationData:
        # Step 1: Format check
        if not self.validate_identifier_format(unit_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "success": False,
                    "error": {
                        "code": "INVALID_IDENTIFIER_FORMAT",
                        "message": f"Service unit identifier '{unit_id}' has an invalid format."
                    }
                }
            )

        # Step 2: Query service unit by ID or Code
        unit = self.repository.get_by_id(unit_id)
        if not unit:
            unit = self.repository.get_by_code(unit_id)

        if not unit:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "success": False,
                    "error": {
                        "code": "SERVICE_UNIT_NOT_FOUND",
                        "message": f"Service unit with identifier '{unit_id}' was not found."
                    }
                }
            )

        return ServiceUnitValidationData(
            unit_id=unit.id,
            code=unit.code,
            name=unit.name,
            description=unit.description,
            is_valid=True
        )
