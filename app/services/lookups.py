from fastapi import status
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.validators import ensure_identifier
from app.models.department import Department
from app.models.faculty import Faculty
from app.models.service_unit import ServiceUnit
from app.repositories.department_repository import DepartmentRepository
from app.repositories.faculty_repository import FacultyRepository
from app.repositories.service_unit_repository import ServiceUnitRepository


def _by_id_or_code(repository, identifier: str):
    return repository.get_by_id(identifier) or repository.get_by_code(identifier.upper())


class DirectoryLookup:
    """Resolve directory entities by identifier or code, raising the standard 400/404 errors."""

    def __init__(self, db: Session):
        self.faculties = FacultyRepository(db)
        self.departments = DepartmentRepository(db)
        self.service_units = ServiceUnitRepository(db)

    def faculty(self, identifier: str) -> Faculty:
        key = ensure_identifier(identifier, "Faculty")
        faculty = _by_id_or_code(self.faculties, key)
        if not faculty:
            raise AppError(
                status.HTTP_404_NOT_FOUND,
                "FACULTY_NOT_FOUND",
                f"Faculty with identifier '{identifier}' was not found.",
            )
        return faculty

    def department(self, identifier: str) -> Department:
        key = ensure_identifier(identifier, "Department")
        department = _by_id_or_code(self.departments, key)
        if not department:
            raise AppError(
                status.HTTP_404_NOT_FOUND,
                "DEPARTMENT_NOT_FOUND",
                f"Department with identifier '{identifier}' was not found.",
            )
        return department

    def service_unit(self, identifier: str) -> ServiceUnit:
        key = ensure_identifier(identifier, "Service unit")
        unit = _by_id_or_code(self.service_units, key)
        if not unit:
            raise AppError(
                status.HTTP_404_NOT_FOUND,
                "SERVICE_UNIT_NOT_FOUND",
                f"Service unit with identifier '{identifier}' was not found.",
            )
        return unit


def ensure_department_in_faculty(department: Department, faculty: Faculty) -> None:
    if department.faculty_id != faculty.id:
        raise AppError(
            status.HTTP_400_BAD_REQUEST,
            "INVALID_ORGANIZATIONAL_RELATIONSHIP",
            f"Department '{department.name}' does not belong to the specified Faculty '{faculty.name}'.",
        )
