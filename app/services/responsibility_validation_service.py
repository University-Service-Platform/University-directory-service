from sqlalchemy.orm import Session
from fastapi import status
from typing import Optional, List
from app.core.errors import AppError
from app.core.validators import ensure_identifier
from app.repositories.responsibility_repository import ServiceResponsibilityRepository
from app.models.service_responsibility import ResponsibilityStatus
from app.schemas.responsibility_validation import (
    UserResponsibilityValidationData,
    ResponsibilityRecordData
)

class ServiceResponsibilityValidationService:
    def __init__(self, db: Session):
        self.repository = ServiceResponsibilityRepository(db)

    def validate_user_responsibilities(
        self,
        user_id: str,
        service_unit_id: Optional[str] = None,
        department_id: Optional[str] = None,
        faculty_id: Optional[str] = None
    ) -> UserResponsibilityValidationData:
        # Step 1: Format validation
        ensure_identifier(user_id, "User")

        # Step 2: Retrieve actual responsibility relationship records
        records = self.repository.get_by_user_id(
            user_id=user_id,
            service_unit_id=service_unit_id,
            department_id=department_id,
            faculty_id=faculty_id
        )

        if not records:
            raise AppError(
                status.HTTP_404_NOT_FOUND,
                "RESPONSIBILITY_NOT_FOUND",
                f"No active responsibility relationship exists for user '{user_id}' matching the requested criteria."
            )

        # Step 3: Build response records
        resp_list: List[ResponsibilityRecordData] = []
        has_active = False

        for r in records:
            if r.status == ResponsibilityStatus.ACTIVE:
                has_active = True

            resp_list.append(
                ResponsibilityRecordData(
                    responsibility_id=r.id,
                    user_id=r.user_id,
                    service_unit_id=r.service_unit_id,
                    service_unit_name=r.service_unit.name if r.service_unit else None,
                    department_id=r.department_id,
                    department_name=r.department.name if r.department else None,
                    faculty_id=r.faculty_id,
                    faculty_name=r.faculty.name if r.faculty else None,
                    role_title=r.role_title,
                    status=r.status
                )
            )

        if not has_active:
            raise AppError(
                status.HTTP_403_FORBIDDEN,
                "RESPONSIBILITY_INACTIVE",
                f"Service responsibility relationship for user '{user_id}' is inactive."
            )

        return UserResponsibilityValidationData(
            user_id=user_id,
            is_valid=has_active,
            responsibilities=resp_list
        )
