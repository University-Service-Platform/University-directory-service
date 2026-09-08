from sqlalchemy.orm import Session
from fastapi import HTTPException, status
import uuid
import re
from typing import List
from datetime import datetime

from app.models.service_unit import ServiceUnit
from app.repositories.service_unit_repository import ServiceUnitRepository
from app.schemas.service_unit import ServiceUnitCreate, ServiceUnitUpdate, ServiceUnitResponse

class ServiceUnitManagementService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = ServiceUnitRepository(db)

    @staticmethod
    def validate_code_format(code: str) -> bool:
        if not code or not isinstance(code, str):
            return False
        pattern = r"^[a-zA-Z0-9_-]{2,20}$"
        return bool(re.match(pattern, code.strip()))

    @staticmethod
    def validate_identifier_format(service_unit_id: str) -> bool:
        if not service_unit_id or not isinstance(service_unit_id, str):
            return False
        pattern = r"^[a-zA-Z0-9_-]{2,50}$"
        return bool(re.match(pattern, service_unit_id.strip()))

    def _to_response(self, service_unit: ServiceUnit) -> ServiceUnitResponse:
        return ServiceUnitResponse(
            id=service_unit.id,
            code=service_unit.code,
            name=service_unit.name,
            description=service_unit.description,
            created_at=service_unit.created_at
        )

    def create_service_unit(self, service_unit_in: ServiceUnitCreate) -> ServiceUnitResponse:
        normalized_code = service_unit_in.code.strip().upper()
        if not self.validate_code_format(normalized_code):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "success": False,
                    "error": {
                        "code": "INVALID_IDENTIFIER_FORMAT",
                        "message": f"Service unit code '{service_unit_in.code}' has an invalid format."
                    }
                }
            )

        # Check duplicate code
        if self.repository.get_by_code(normalized_code):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "success": False,
                    "error": {
                        "code": "SERVICE_UNIT_CODE_ALREADY_EXISTS",
                        "message": f"Service unit with code '{normalized_code}' already exists."
                    }
                }
            )

        new_unit = ServiceUnit(
            id=f"unit-{normalized_code.lower()}-{uuid.uuid4().hex[:6]}",
            code=normalized_code,
            name=service_unit_in.name.strip(),
            description=service_unit_in.description.strip() if service_unit_in.description else None,
            created_at=datetime.utcnow()
        )

        persisted = self.repository.create(new_unit)
        return self._to_response(persisted)

    def list_service_units(self, skip: int = 0, limit: int = 100) -> List[ServiceUnitResponse]:
        units = self.repository.list_all(skip=skip, limit=limit)
        return [self._to_response(u) for u in units]

    def get_service_unit(self, service_unit_id: str) -> ServiceUnitResponse:
        if not self.validate_identifier_format(service_unit_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "success": False,
                    "error": {
                        "code": "INVALID_IDENTIFIER_FORMAT",
                        "message": f"Service unit identifier '{service_unit_id}' has an invalid format."
                    }
                }
            )

        unit = self.repository.get_by_id(service_unit_id)
        if not unit:
            unit = self.repository.get_by_code(service_unit_id.strip().upper())

        if not unit:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "success": False,
                    "error": {
                        "code": "SERVICE_UNIT_NOT_FOUND",
                        "message": f"Service unit with identifier '{service_unit_id}' was not found."
                    }
                }
            )

        return self._to_response(unit)

    def update_service_unit(self, service_unit_id: str, service_unit_update: ServiceUnitUpdate) -> ServiceUnitResponse:
        if not self.validate_identifier_format(service_unit_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "success": False,
                    "error": {
                        "code": "INVALID_IDENTIFIER_FORMAT",
                        "message": f"Service unit identifier '{service_unit_id}' has an invalid format."
                    }
                }
            )

        unit = self.repository.get_by_id(service_unit_id)
        if not unit:
            unit = self.repository.get_by_code(service_unit_id.strip().upper())

        if not unit:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "success": False,
                    "error": {
                        "code": "SERVICE_UNIT_NOT_FOUND",
                        "message": f"Service unit with identifier '{service_unit_id}' was not found."
                    }
                }
            )

        if service_unit_update.code is not None:
            new_code = service_unit_update.code.strip().upper()
            if not self.validate_code_format(new_code):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "success": False,
                        "error": {
                            "code": "INVALID_IDENTIFIER_FORMAT",
                            "message": f"Service unit code '{new_code}' has an invalid format."
                        }
                    }
                )
            existing = self.repository.get_by_code(new_code)
            if existing and existing.id != unit.id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "success": False,
                        "error": {
                            "code": "SERVICE_UNIT_CODE_ALREADY_EXISTS",
                            "message": f"Service unit with code '{new_code}' already exists."
                        }
                    }
                )
            unit.code = new_code

        if service_unit_update.name is not None:
            unit.name = service_unit_update.name.strip()

        if service_unit_update.description is not None:
            unit.description = service_unit_update.description.strip()

        updated = self.repository.update(unit)
        return self._to_response(updated)

    def delete_service_unit(self, service_unit_id: str) -> None:
        if not self.validate_identifier_format(service_unit_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "success": False,
                    "error": {
                        "code": "INVALID_IDENTIFIER_FORMAT",
                        "message": f"Service unit identifier '{service_unit_id}' has an invalid format."
                    }
                }
            )

        unit = self.repository.get_by_id(service_unit_id)
        if not unit:
            unit = self.repository.get_by_code(service_unit_id.strip().upper())

        if not unit:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "success": False,
                    "error": {
                        "code": "SERVICE_UNIT_NOT_FOUND",
                        "message": f"Service unit with identifier '{service_unit_id}' was not found."
                    }
                }
            )

        self.repository.delete(unit)
