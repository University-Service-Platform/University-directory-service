from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.faculty_management_service import FacultyManagementService
from app.schemas.faculty import (
    FacultyCreate,
    FacultyUpdate,
    FacultySingleResponse,
    FacultyListResponse
)

router = APIRouter(tags=["Faculties"])

@router.post(
    "/faculties",
    response_model=FacultySingleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Faculty",
    description="Create a new academic faculty record."
)
def create_faculty(
    faculty_in: FacultyCreate,
    db: Session = Depends(get_db)
):
    service = FacultyManagementService(db)
    faculty_data = service.create_faculty(faculty_in)
    return FacultySingleResponse(success=True, data=faculty_data)

@router.get(
    "/faculties",
    response_model=FacultyListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Faculties",
    description="Retrieve a list of all academic faculties."
)
def list_faculties(
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(100, ge=1, le=500, description="Max items to return"),
    db: Session = Depends(get_db)
):
    service = FacultyManagementService(db)
    faculties_data = service.list_faculties(skip=skip, limit=limit)
    return FacultyListResponse(success=True, data=faculties_data)

@router.get(
    "/faculties/{faculty_id}",
    response_model=FacultySingleResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Faculty by ID or Code",
    description="Retrieve details for a specific faculty by its identifier or faculty code."
)
def get_faculty(
    faculty_id: str,
    db: Session = Depends(get_db)
):
    service = FacultyManagementService(db)
    faculty_data = service.get_faculty(faculty_id)
    return FacultySingleResponse(success=True, data=faculty_data)

@router.put(
    "/faculties/{faculty_id}",
    response_model=FacultySingleResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Faculty",
    description="Update permitted details (name, description, code) of an existing faculty."
)
def update_faculty(
    faculty_id: str,
    faculty_update: FacultyUpdate,
    db: Session = Depends(get_db)
):
    service = FacultyManagementService(db)
    updated_data = service.update_faculty(faculty_id=faculty_id, faculty_update=faculty_update)
    return FacultySingleResponse(success=True, data=updated_data)

@router.delete(
    "/faculties/{faculty_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete Faculty",
    description="Permanently delete a faculty record."
)
def delete_faculty(
    faculty_id: str,
    db: Session = Depends(get_db)
):
    service = FacultyManagementService(db)
    service.delete_faculty(faculty_id)
    return {
        "success": True,
        "data": {
            "message": f"Faculty '{faculty_id}' was successfully deleted."
        }
    }
