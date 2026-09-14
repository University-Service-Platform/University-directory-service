from sqlalchemy.orm import Session
from fastapi import HTTPException, status
import uuid
import re
from typing import List, Optional
from datetime import datetime

from app.models.user_affiliation import UserAffiliation
from app.repositories.affiliation_repository import AffiliationRepository
from app.repositories.department_repository import DepartmentRepository
from app.repositories.faculty_repository import FacultyRepository
from app.schemas.affiliation import AffiliationCreate, AffiliationUpdate, AffiliationResponse

class AffiliationManagementService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = AffiliationRepository(db)
        self.department_repository = DepartmentRepository(db)
        self.faculty_repository = FacultyRepository(db)

    @staticmethod
    def validate_identifier_format(identifier: str) -> bool:
        if not identifier or not isinstance(identifier, str):
            return False
        pattern = r"^[a-zA-Z0-9_-]{2,50}$"
        return bool(re.match(pattern, identifier.strip()))

    def _to_response(self, affiliation: UserAffiliation) -> AffiliationResponse:
        return AffiliationResponse(
            id=affiliation.id,
            user_id=affiliation.user_id,
            department_id=affiliation.department_id,
            department_name=affiliation.department.name if affiliation.department else None,
            department_code=affiliation.department.code if affiliation.department else None,
            faculty_id=affiliation.faculty_id,
            faculty_name=affiliation.faculty.name if affiliation.faculty else None,
            faculty_code=affiliation.faculty.code if affiliation.faculty else None,
            created_at=affiliation.created_at,
            updated_at=affiliation.updated_at
        )

    def create_affiliation(self, affiliation_in: AffiliationCreate) -> AffiliationResponse:
        # Step 1: Validate identifier formats
        if not self.validate_identifier_format(affiliation_in.user_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "success": False,
                    "error": {
                        "code": "INVALID_IDENTIFIER_FORMAT",
                        "message": f"User identifier '{affiliation_in.user_id}' has an invalid format."
                    }
                }
            )

        if not self.validate_identifier_format(affiliation_in.department_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "success": False,
                    "error": {
                        "code": "INVALID_IDENTIFIER_FORMAT",
                        "message": f"Department identifier '{affiliation_in.department_id}' has an invalid format."
                    }
                }
            )

        # Step 2: Validate Department existence
        dept = self.department_repository.get_by_id(affiliation_in.department_id.strip())
        if not dept:
            dept = self.department_repository.get_by_code(affiliation_in.department_id.strip().upper())

        if not dept:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "success": False,
                    "error": {
                        "code": "DEPARTMENT_NOT_FOUND",
                        "message": f"Department with identifier '{affiliation_in.department_id}' was not found."
                    }
                }
            )

        # Step 3: Faculty existence and Relationship validation
        target_faculty_id = dept.faculty_id

        if affiliation_in.faculty_id:
            if not self.validate_identifier_format(affiliation_in.faculty_id):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "success": False,
                        "error": {
                            "code": "INVALID_IDENTIFIER_FORMAT",
                            "message": f"Faculty identifier '{affiliation_in.faculty_id}' has an invalid format."
                        }
                    }
                )

            faculty = self.faculty_repository.get_by_id(affiliation_in.faculty_id.strip())
            if not faculty:
                faculty = self.faculty_repository.get_by_code(affiliation_in.faculty_id.strip().upper())

            if not faculty:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={
                        "success": False,
                        "error": {
                            "code": "FACULTY_NOT_FOUND",
                            "message": f"Faculty with identifier '{affiliation_in.faculty_id}' was not found."
                        }
                    }
                )

            if dept.faculty_id != faculty.id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "success": False,
                        "error": {
                            "code": "INVALID_ORGANIZATIONAL_RELATIONSHIP",
                            "message": f"Department '{dept.name}' does not belong to the specified Faculty '{faculty.name}'."
                        }
                    }
                )
            target_faculty_id = faculty.id

        # Step 4: Duplicate affiliation check
        existing = self.repository.get_by_user_and_department(
            user_id=affiliation_in.user_id.strip(),
            department_id=dept.id
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "success": False,
                    "error": {
                        "code": "AFFILIATION_ALREADY_EXISTS",
                        "message": f"User '{affiliation_in.user_id}' is already affiliated with Department '{dept.name}'."
                    }
                }
            )

        # Step 5: Persist affiliation
        new_aff = UserAffiliation(
            id=f"aff-{affiliation_in.user_id.strip().lower()}-{uuid.uuid4().hex[:6]}",
            user_id=affiliation_in.user_id.strip(),
            department_id=dept.id,
            faculty_id=target_faculty_id,
            created_at=datetime.utcnow()
        )

        persisted = self.repository.create(new_aff)
        return self._to_response(persisted)

    def get_affiliation(self, affiliation_id: str) -> AffiliationResponse:
        if not self.validate_identifier_format(affiliation_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "success": False,
                    "error": {
                        "code": "INVALID_IDENTIFIER_FORMAT",
                        "message": f"Affiliation identifier '{affiliation_id}' has an invalid format."
                    }
                }
            )

        aff = self.repository.get_by_id(affiliation_id)
        if not aff:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "success": False,
                    "error": {
                        "code": "AFFILIATION_NOT_FOUND",
                        "message": f"Affiliation with identifier '{affiliation_id}' was not found."
                    }
                }
            )

        return self._to_response(aff)

    def get_user_affiliation(self, user_id: str) -> AffiliationResponse:
        if not self.validate_identifier_format(user_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "success": False,
                    "error": {
                        "code": "INVALID_IDENTIFIER_FORMAT",
                        "message": f"User identifier '{user_id}' has an invalid format."
                    }
                }
            )

        aff = self.repository.get_by_user_id(user_id.strip())
        if not aff:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "success": False,
                    "error": {
                        "code": "AFFILIATION_NOT_FOUND",
                        "message": f"No organizational affiliation found for user '{user_id}'."
                    }
                }
            )

        return self._to_response(aff)

    def list_affiliations(
        self,
        skip: int = 0,
        limit: int = 100,
        department_id: Optional[str] = None,
        faculty_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> List[AffiliationResponse]:
        affiliations = self.repository.list_all(
            skip=skip,
            limit=limit,
            department_id=department_id,
            faculty_id=faculty_id,
            user_id=user_id
        )
        return [self._to_response(a) for a in affiliations]

    def update_affiliation(
        self,
        affiliation_id: str,
        affiliation_update: AffiliationUpdate
    ) -> AffiliationResponse:
        if not self.validate_identifier_format(affiliation_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "success": False,
                    "error": {
                        "code": "INVALID_IDENTIFIER_FORMAT",
                        "message": f"Affiliation identifier '{affiliation_id}' has an invalid format."
                    }
                }
            )

        aff = self.repository.get_by_id(affiliation_id)
        if not aff:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "success": False,
                    "error": {
                        "code": "AFFILIATION_NOT_FOUND",
                        "message": f"Affiliation with identifier '{affiliation_id}' was not found."
                    }
                }
            )

        target_dept = aff.department
        if affiliation_update.department_id is not None:
            if not self.validate_identifier_format(affiliation_update.department_id):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "success": False,
                        "error": {
                            "code": "INVALID_IDENTIFIER_FORMAT",
                            "message": f"Department identifier '{affiliation_update.department_id}' has an invalid format."
                        }
                    }
                )

            dept = self.department_repository.get_by_id(affiliation_update.department_id.strip())
            if not dept:
                dept = self.department_repository.get_by_code(affiliation_update.department_id.strip().upper())

            if not dept:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={
                        "success": False,
                        "error": {
                            "code": "DEPARTMENT_NOT_FOUND",
                            "message": f"Department with identifier '{affiliation_update.department_id}' was not found."
                        }
                    }
                )
            target_dept = dept

        target_faculty_id = target_dept.faculty_id
        if affiliation_update.faculty_id is not None:
            if not self.validate_identifier_format(affiliation_update.faculty_id):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "success": False,
                        "error": {
                            "code": "INVALID_IDENTIFIER_FORMAT",
                            "message": f"Faculty identifier '{affiliation_update.faculty_id}' has an invalid format."
                        }
                    }
                )

            faculty = self.faculty_repository.get_by_id(affiliation_update.faculty_id.strip())
            if not faculty:
                faculty = self.faculty_repository.get_by_code(affiliation_update.faculty_id.strip().upper())

            if not faculty:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={
                        "success": False,
                        "error": {
                            "code": "FACULTY_NOT_FOUND",
                            "message": f"Faculty with identifier '{affiliation_update.faculty_id}' was not found."
                        }
                    }
                )

            if target_dept.faculty_id != faculty.id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "success": False,
                        "error": {
                            "code": "INVALID_ORGANIZATIONAL_RELATIONSHIP",
                            "message": f"Department '{target_dept.name}' does not belong to the specified Faculty '{faculty.name}'."
                        }
                    }
                )
            target_faculty_id = faculty.id

        if affiliation_update.department_id is not None and target_dept.id != aff.department_id:
            existing = self.repository.get_by_user_and_department(
                user_id=aff.user_id,
                department_id=target_dept.id
            )
            if existing and existing.id != aff.id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "success": False,
                        "error": {
                            "code": "AFFILIATION_ALREADY_EXISTS",
                            "message": f"User '{aff.user_id}' is already affiliated with Department '{target_dept.name}'."
                        }
                    }
                )
            aff.department_id = target_dept.id
            aff.faculty_id = target_faculty_id

        aff.updated_at = datetime.utcnow()
        updated = self.repository.update(aff)
        return self._to_response(updated)

    def delete_affiliation(self, affiliation_id: str) -> None:
        if not self.validate_identifier_format(affiliation_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "success": False,
                    "error": {
                        "code": "INVALID_IDENTIFIER_FORMAT",
                        "message": f"Affiliation identifier '{affiliation_id}' has an invalid format."
                    }
                }
            )

        aff = self.repository.get_by_id(affiliation_id)
        if not aff:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "success": False,
                    "error": {
                        "code": "AFFILIATION_NOT_FOUND",
                        "message": f"Affiliation with identifier '{affiliation_id}' was not found."
                    }
                }
            )

        self.repository.delete(aff)
