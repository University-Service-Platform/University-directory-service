from sqlalchemy.orm import Session
from fastapi import HTTPException, status
import uuid
import re
from typing import List, Optional
from datetime import datetime

from app.models.department import Department
from app.repositories.department_repository import DepartmentRepository
from app.repositories.faculty_repository import FacultyRepository
from app.schemas.department import DepartmentCreate, DepartmentUpdate, DepartmentResponse

class DepartmentManagementService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = DepartmentRepository(db)
        self.faculty_repository = FacultyRepository(db)

    @staticmethod
    def validate_code_format(code: str) -> bool:
        if not code or not isinstance(code, str):
            return False
        pattern = r"^[a-zA-Z0-9_-]{2,20}$"
        return bool(re.match(pattern, code.strip()))

    @staticmethod
    def validate_identifier_format(department_id: str) -> bool:
        if not department_id or not isinstance(department_id, str):
            return False
        pattern = r"^[a-zA-Z0-9_-]{2,50}$"
        return bool(re.match(pattern, department_id.strip()))

    def _to_response(self, department: Department) -> DepartmentResponse:
        return DepartmentResponse(
            id=department.id,
            code=department.code,
            name=department.name,
            faculty_id=department.faculty_id,
            created_at=department.created_at,
            updated_at=department.updated_at
        )

    def create_department(self, department_in: DepartmentCreate) -> DepartmentResponse:
        normalized_code = department_in.code.strip().upper()
        if not self.validate_code_format(normalized_code):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "success": False,
                    "error": {
                        "code": "INVALID_IDENTIFIER_FORMAT",
                        "message": f"Department code '{department_in.code}' has an invalid format."
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
                        "code": "DEPARTMENT_CODE_ALREADY_EXISTS",
                        "message": f"Department with code '{normalized_code}' already exists."
                    }
                }
            )

        # Validate faculty exists
        faculty = self.faculty_repository.get_by_id(department_in.faculty_id.strip())
        if not faculty:
            faculty = self.faculty_repository.get_by_code(department_in.faculty_id.strip().upper())

        if not faculty:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "success": False,
                    "error": {
                        "code": "FACULTY_NOT_FOUND",
                        "message": f"Faculty with identifier '{department_in.faculty_id}' was not found."
                    }
                }
            )

        new_dept = Department(
            id=f"dept-{normalized_code.lower()}-{uuid.uuid4().hex[:6]}",
            code=normalized_code,
            name=department_in.name.strip(),
            faculty_id=faculty.id,
            created_at=datetime.utcnow()
        )

        persisted = self.repository.create(new_dept)
        return self._to_response(persisted)

    def list_departments(
        self,
        skip: int = 0,
        limit: int = 100,
        faculty_id: Optional[str] = None
    ) -> List[DepartmentResponse]:
        departments = self.repository.list_all(skip=skip, limit=limit, faculty_id=faculty_id)
        return [self._to_response(d) for d in departments]

    def get_department(self, department_id: str) -> DepartmentResponse:
        if not self.validate_identifier_format(department_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "success": False,
                    "error": {
                        "code": "INVALID_IDENTIFIER_FORMAT",
                        "message": f"Department identifier '{department_id}' has an invalid format."
                    }
                }
            )

        dept = self.repository.get_by_id(department_id)
        if not dept:
            dept = self.repository.get_by_code(department_id.strip().upper())

        if not dept:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "success": False,
                    "error": {
                        "code": "DEPARTMENT_NOT_FOUND",
                        "message": f"Department with identifier '{department_id}' was not found."
                    }
                }
            )

        return self._to_response(dept)

    def update_department(self, department_id: str, department_update: DepartmentUpdate) -> DepartmentResponse:
        if not self.validate_identifier_format(department_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "success": False,
                    "error": {
                        "code": "INVALID_IDENTIFIER_FORMAT",
                        "message": f"Department identifier '{department_id}' has an invalid format."
                    }
                }
            )

        dept = self.repository.get_by_id(department_id)
        if not dept:
            dept = self.repository.get_by_code(department_id.strip().upper())

        if not dept:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "success": False,
                    "error": {
                        "code": "DEPARTMENT_NOT_FOUND",
                        "message": f"Department with identifier '{department_id}' was not found."
                    }
                }
            )

        if department_update.code is not None:
            new_code = department_update.code.strip().upper()
            if not self.validate_code_format(new_code):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "success": False,
                        "error": {
                            "code": "INVALID_IDENTIFIER_FORMAT",
                            "message": f"Department code '{new_code}' has an invalid format."
                        }
                    }
                )
            existing = self.repository.get_by_code(new_code)
            if existing and existing.id != dept.id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "success": False,
                        "error": {
                            "code": "DEPARTMENT_CODE_ALREADY_EXISTS",
                            "message": f"Department with code '{new_code}' already exists."
                        }
                    }
                )
            dept.code = new_code

        if department_update.name is not None:
            dept.name = department_update.name.strip()

        if department_update.faculty_id is not None:
            faculty = self.faculty_repository.get_by_id(department_update.faculty_id.strip())
            if not faculty:
                faculty = self.faculty_repository.get_by_code(department_update.faculty_id.strip().upper())

            if not faculty:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={
                        "success": False,
                        "error": {
                            "code": "FACULTY_NOT_FOUND",
                            "message": f"Faculty with identifier '{department_update.faculty_id}' was not found."
                        }
                    }
                )
            dept.faculty_id = faculty.id

        dept.updated_at = datetime.utcnow()
        updated = self.repository.update(dept)
        return self._to_response(updated)

    def delete_department(self, department_id: str) -> None:
        if not self.validate_identifier_format(department_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "success": False,
                    "error": {
                        "code": "INVALID_IDENTIFIER_FORMAT",
                        "message": f"Department identifier '{department_id}' has an invalid format."
                    }
                }
            )

        dept = self.repository.get_by_id(department_id)
        if not dept:
            dept = self.repository.get_by_code(department_id.strip().upper())

        if not dept:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "success": False,
                    "error": {
                        "code": "DEPARTMENT_NOT_FOUND",
                        "message": f"Department with identifier '{department_id}' was not found."
                    }
                }
            )

        self.repository.delete(dept)
