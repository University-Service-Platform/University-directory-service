from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.auth import get_current_user, require_admin
from app.database import get_db
from app.integrations.identity_client import IdentityClient, get_identity_client
from app.models.service_responsibility import ResponsibilityStatus
from app.services.responsibility_management_service import ResponsibilityManagementService
from app.schemas.responsibility import (
    ResponsibilityCreate,
    ResponsibilityUpdate,
    ResponsibilitySingleResponse,
    ResponsibilityListResponse
)

router = APIRouter(tags=["Service Responsibilities"], dependencies=[Depends(get_current_user)])

@router.post(
    "/responsibilities",
    dependencies=[Depends(require_admin)],
    response_model=ResponsibilitySingleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Service Responsibility",
    description="Assign a responsibility to a user for a service unit, department and/or faculty. "
                "Referenced units must exist; an ACTIVE responsibility requires the user to be ACTIVE "
                "in the Identity Service and must not duplicate another ACTIVE one for the same scope."
)
def create_responsibility(
    responsibility_in: ResponsibilityCreate,
    db: Session = Depends(get_db),
    identity_client: IdentityClient = Depends(get_identity_client)
):
    service = ResponsibilityManagementService(db, identity_client)
    return ResponsibilitySingleResponse(success=True, data=service.create_responsibility(responsibility_in))

@router.get(
    "/responsibilities",
    response_model=ResponsibilityListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Service Responsibilities",
    description="List service responsibilities with optional filters and pagination."
)
def list_responsibilities(
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(100, ge=1, le=500, description="Max items to return"),
    user_id: Optional[str] = Query(None, description="Filter by user identifier"),
    service_unit_id: Optional[str] = Query(None, description="Filter by service unit identifier"),
    department_id: Optional[str] = Query(None, description="Filter by department identifier"),
    faculty_id: Optional[str] = Query(None, description="Filter by faculty identifier"),
    status_filter: Optional[ResponsibilityStatus] = Query(None, alias="status", description="Filter by status"),
    q: Optional[str] = Query(None, max_length=100, description="Case-insensitive search in user id, role title "
                                                               "and unit/department/faculty code and name"),
    db: Session = Depends(get_db)
):
    service = ResponsibilityManagementService(db)
    data = service.list_responsibilities(
        skip=skip,
        limit=limit,
        user_id=user_id,
        service_unit_id=service_unit_id,
        department_id=department_id,
        faculty_id=faculty_id,
        status_filter=status_filter,
        q=q
    )
    return ResponsibilityListResponse(success=True, data=data)

@router.get(
    "/responsibilities/{responsibility_id}",
    response_model=ResponsibilitySingleResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Service Responsibility",
    description="Retrieve a single service responsibility."
)
def get_responsibility(
    responsibility_id: str,
    db: Session = Depends(get_db)
):
    service = ResponsibilityManagementService(db)
    return ResponsibilitySingleResponse(success=True, data=service.get_responsibility(responsibility_id))

@router.put(
    "/responsibilities/{responsibility_id}",
    dependencies=[Depends(require_admin)],
    response_model=ResponsibilitySingleResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Service Responsibility",
    description="Update the title, status or organizational scope of a responsibility. "
                "Deactivating does not require the user to be active in the Identity Service."
)
def update_responsibility(
    responsibility_id: str,
    responsibility_update: ResponsibilityUpdate,
    db: Session = Depends(get_db),
    identity_client: IdentityClient = Depends(get_identity_client)
):
    service = ResponsibilityManagementService(db, identity_client)
    data = service.update_responsibility(responsibility_id, responsibility_update)
    return ResponsibilitySingleResponse(success=True, data=data)

@router.delete(
    "/responsibilities/{responsibility_id}",
    dependencies=[Depends(require_admin)],
    status_code=status.HTTP_200_OK,
    summary="Delete Service Responsibility",
    description="Permanently delete a service responsibility record."
)
def delete_responsibility(
    responsibility_id: str,
    db: Session = Depends(get_db)
):
    service = ResponsibilityManagementService(db)
    service.delete_responsibility(responsibility_id)
    return {
        "success": True,
        "data": {
            "message": f"Responsibility '{responsibility_id}' was successfully deleted."
        }
    }
