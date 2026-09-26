from sqlalchemy.orm import Session
from fastapi import status
import uuid
from typing import List, Optional

from app.core.errors import AppError
from app.core.time import utc_now
from app.core.validators import ensure_code
from app.models.service_unit import ServiceUnit
from app.repositories.service_unit_repository import ServiceUnitRepository
from app.schemas.service_unit import ServiceUnitCreate, ServiceUnitUpdate, ServiceUnitResponse
from app.services.lookups import DirectoryLookup

class ServiceUnitManagementService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = ServiceUnitRepository(db)
        self.lookup = DirectoryLookup(db)

    def _to_response(self, service_unit: ServiceUnit) -> ServiceUnitResponse:
        return ServiceUnitResponse(
            id=service_unit.id,
            code=service_unit.code,
            name=service_unit.name,
            description=service_unit.description,
            created_at=service_unit.created_at
        )

    def _ensure_code_available(self, code: str, current_id: Optional[str] = None) -> None:
        existing = self.repository.get_by_code(code)
        if existing and existing.id != current_id:
            raise AppError(
                status.HTTP_409_CONFLICT,
                "SERVICE_UNIT_CODE_ALREADY_EXISTS",
                f"Service unit with code '{code}' already exists."
            )

    def create_service_unit(self, service_unit_in: ServiceUnitCreate) -> ServiceUnitResponse:
        normalized_code = service_unit_in.code.strip().upper()
        ensure_code(normalized_code, "Service unit", display=service_unit_in.code)
        self._ensure_code_available(normalized_code)

        new_unit = ServiceUnit(
            id=f"unit-{normalized_code.lower()}-{uuid.uuid4().hex[:6]}",
            code=normalized_code,
            name=service_unit_in.name.strip(),
            description=service_unit_in.description.strip() if service_unit_in.description else None,
            created_at=utc_now()
        )

        persisted = self.repository.create(new_unit)
        return self._to_response(persisted)

    def list_service_units(self, skip: int = 0, limit: int = 100) -> List[ServiceUnitResponse]:
        units = self.repository.list_all(skip=skip, limit=limit)
        return [self._to_response(u) for u in units]

    def get_service_unit(self, service_unit_id: str) -> ServiceUnitResponse:
        return self._to_response(self.lookup.service_unit(service_unit_id))

    def update_service_unit(self, service_unit_id: str, service_unit_update: ServiceUnitUpdate) -> ServiceUnitResponse:
        unit = self.lookup.service_unit(service_unit_id)

        if service_unit_update.code is not None:
            new_code = service_unit_update.code.strip().upper()
            ensure_code(new_code, "Service unit")
            self._ensure_code_available(new_code, current_id=unit.id)
            unit.code = new_code

        if service_unit_update.name is not None:
            unit.name = service_unit_update.name.strip()

        if service_unit_update.description is not None:
            unit.description = service_unit_update.description.strip()

        updated = self.repository.update(unit)
        return self._to_response(updated)

    def delete_service_unit(self, service_unit_id: str) -> None:
        unit = self.lookup.service_unit(service_unit_id)
        self.repository.delete(unit)
