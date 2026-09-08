from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.service_unit_management_service import ServiceUnitManagementService
from app.schemas.service_unit import (
    ServiceUnitCreate,
    ServiceUnitUpdate,
    ServiceUnitSingleResponse,
    ServiceUnitListResponse
)

router = APIRouter(tags=["Service Units"])

@router.post(
    "/service-units",
    response_model=ServiceUnitSingleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Service Unit",
    description="Create a new non-academic central service unit record."
)
def create_service_unit(
    service_unit_in: ServiceUnitCreate,
    db: Session = Depends(get_db)
):
    service = ServiceUnitManagementService(db)
    unit_data = service.create_service_unit(service_unit_in)
    return ServiceUnitSingleResponse(success=True, data=unit_data)

@router.get(
    "/service-units",
    response_model=ServiceUnitListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Service Units",
    description="Retrieve a list of all non-academic central service units."
)
def list_service_units(
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(100, ge=1, le=500, description="Max items to return"),
    db: Session = Depends(get_db)
):
    service = ServiceUnitManagementService(db)
    units_data = service.list_service_units(skip=skip, limit=limit)
    return ServiceUnitListResponse(success=True, data=units_data)

@router.get(
    "/service-units/{service_unit_id}",
    response_model=ServiceUnitSingleResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Service Unit by ID or Code",
    description="Retrieve details for a specific service unit by its identifier or unit code."
)
def get_service_unit(
    service_unit_id: str,
    db: Session = Depends(get_db)
):
    service = ServiceUnitManagementService(db)
    unit_data = service.get_service_unit(service_unit_id)
    return ServiceUnitSingleResponse(success=True, data=unit_data)

@router.put(
    "/service-units/{service_unit_id}",
    response_model=ServiceUnitSingleResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Service Unit",
    description="Update permitted details (name, description, code) of an existing service unit."
)
def update_service_unit(
    service_unit_id: str,
    service_unit_update: ServiceUnitUpdate,
    db: Session = Depends(get_db)
):
    service = ServiceUnitManagementService(db)
    updated_data = service.update_service_unit(service_unit_id=service_unit_id, service_unit_update=service_unit_update)
    return ServiceUnitSingleResponse(success=True, data=updated_data)

@router.delete(
    "/service-units/{service_unit_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete Service Unit",
    description="Permanently delete a service unit record."
)
def delete_service_unit(
    service_unit_id: str,
    db: Session = Depends(get_db)
):
    service = ServiceUnitManagementService(db)
    service.delete_service_unit(service_unit_id)
    return {
        "success": True,
        "data": {
            "message": f"Service unit '{service_unit_id}' was successfully deleted."
        }
    }
