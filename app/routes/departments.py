from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.database import get_db
from app.services.department_management_service import DepartmentManagementService
from app.schemas.department import (
    DepartmentCreate,
    DepartmentUpdate,
    DepartmentSingleResponse,
    DepartmentListResponse
)

router = APIRouter(tags=["Departments"])

@router.post(
    "/departments",
    response_model=DepartmentSingleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Department",
    description="Create a new academic department record associated with a valid faculty."
)
def create_department(
    department_in: DepartmentCreate,
    db: Session = Depends(get_db)
):
    service = DepartmentManagementService(db)
    dept_data = service.create_department(department_in)
    return DepartmentSingleResponse(success=True, data=dept_data)

@router.get(
    "/departments",
    response_model=DepartmentListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Departments",
    description="Retrieve a list of all academic departments with optional pagination and faculty filtering."
)
def list_departments(
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(100, ge=1, le=500, description="Max items to return"),
    faculty_id: Optional[str] = Query(None, description="Optional filter by parent faculty ID"),
    db: Session = Depends(get_db)
):
    service = DepartmentManagementService(db)
    departments_data = service.list_departments(skip=skip, limit=limit, faculty_id=faculty_id)
    return DepartmentListResponse(success=True, data=departments_data)

@router.get(
    "/departments/{department_id}",
    response_model=DepartmentSingleResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Department by ID or Code",
    description="Retrieve details for a specific department by its identifier or department code."
)
def get_department(
    department_id: str,
    db: Session = Depends(get_db)
):
    service = DepartmentManagementService(db)
    dept_data = service.get_department(department_id)
    return DepartmentSingleResponse(success=True, data=dept_data)

@router.put(
    "/departments/{department_id}",
    response_model=DepartmentSingleResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Department",
    description="Update details (name, code, faculty_id) of an existing department."
)
def update_department(
    department_id: str,
    department_update: DepartmentUpdate,
    db: Session = Depends(get_db)
):
    service = DepartmentManagementService(db)
    updated_data = service.update_department(department_id=department_id, department_update=department_update)
    return DepartmentSingleResponse(success=True, data=updated_data)

@router.patch(
    "/departments/{department_id}",
    response_model=DepartmentSingleResponse,
    status_code=status.HTTP_200_OK,
    summary="Patch Department",
    description="Partially update details of an existing department."
)
def patch_department(
    department_id: str,
    department_update: DepartmentUpdate,
    db: Session = Depends(get_db)
):
    service = DepartmentManagementService(db)
    updated_data = service.update_department(department_id=department_id, department_update=department_update)
    return DepartmentSingleResponse(success=True, data=updated_data)

@router.delete(
    "/departments/{department_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete Department",
    description="Permanently delete a department record."
)
def delete_department(
    department_id: str,
    db: Session = Depends(get_db)
):
    service = DepartmentManagementService(db)
    service.delete_department(department_id)
    return {
        "success": True,
        "data": {
            "message": f"Department '{department_id}' was successfully deleted."
        }
    }
