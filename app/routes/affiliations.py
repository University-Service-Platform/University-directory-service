from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.database import get_db
from app.services.affiliation_management_service import AffiliationManagementService
from app.schemas.affiliation import (
    AffiliationCreate,
    AffiliationUpdate,
    AffiliationSingleResponse,
    AffiliationListResponse
)

router = APIRouter(tags=["Affiliations"])

@router.post(
    "/affiliations",
    response_model=AffiliationSingleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create User Affiliation",
    description="Create an organizational affiliation linking a user to a department and faculty."
)
def create_affiliation(
    affiliation_in: AffiliationCreate,
    db: Session = Depends(get_db)
):
    service = AffiliationManagementService(db)
    affiliation_data = service.create_affiliation(affiliation_in)
    return AffiliationSingleResponse(success=True, data=affiliation_data)

@router.get(
    "/affiliations",
    response_model=AffiliationListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Affiliations",
    description="Retrieve a list of organizational affiliations with optional filters and pagination."
)
def list_affiliations(
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(100, ge=1, le=500, description="Max items to return"),
    department_id: Optional[str] = Query(None, description="Filter by department identifier or code"),
    faculty_id: Optional[str] = Query(None, description="Filter by faculty identifier or code"),
    user_id: Optional[str] = Query(None, description="Filter by user identifier"),
    db: Session = Depends(get_db)
):
    service = AffiliationManagementService(db)
    affiliations_data = service.list_affiliations(
        skip=skip,
        limit=limit,
        department_id=department_id,
        faculty_id=faculty_id,
        user_id=user_id
    )
    return AffiliationListResponse(success=True, data=affiliations_data)

@router.get(
    "/affiliations/users/{user_id}",
    response_model=AffiliationSingleResponse,
    status_code=status.HTTP_200_OK,
    summary="Get User Organizational Affiliation",
    description="Retrieve the current organizational affiliation for a specific user."
)
def get_user_affiliation(
    user_id: str,
    db: Session = Depends(get_db)
):
    service = AffiliationManagementService(db)
    affiliation_data = service.get_user_affiliation(user_id)
    return AffiliationSingleResponse(success=True, data=affiliation_data)

@router.get(
    "/affiliations/{affiliation_id}",
    response_model=AffiliationSingleResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Affiliation by ID",
    description="Retrieve details for a specific affiliation by its unique identifier."
)
def get_affiliation(
    affiliation_id: str,
    db: Session = Depends(get_db)
):
    service = AffiliationManagementService(db)
    affiliation_data = service.get_affiliation(affiliation_id)
    return AffiliationSingleResponse(success=True, data=affiliation_data)

@router.put(
    "/affiliations/{affiliation_id}",
    response_model=AffiliationSingleResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Affiliation",
    description="Update or transfer a user affiliation to another department/faculty."
)
def update_affiliation(
    affiliation_id: str,
    affiliation_update: AffiliationUpdate,
    db: Session = Depends(get_db)
):
    service = AffiliationManagementService(db)
    updated_data = service.update_affiliation(
        affiliation_id=affiliation_id,
        affiliation_update=affiliation_update
    )
    return AffiliationSingleResponse(success=True, data=updated_data)

@router.delete(
    "/affiliations/{affiliation_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete Affiliation",
    description="Permanently delete a user organizational affiliation record."
)
def delete_affiliation(
    affiliation_id: str,
    db: Session = Depends(get_db)
):
    service = AffiliationManagementService(db)
    service.delete_affiliation(affiliation_id)
    return {
        "success": True,
        "data": {
            "message": f"Affiliation '{affiliation_id}' was successfully deleted."
        }
    }
