from pydantic import BaseModel, ConfigDict, Field, model_validator
from typing import Optional, List
from datetime import datetime
from app.models.service_responsibility import ResponsibilityStatus

class ResponsibilityCreate(BaseModel):
    user_id: str = Field(..., min_length=2, max_length=50, description="Identity Service user id or university id (stored as the canonical user id)")
    service_unit_id: Optional[str] = Field(None, min_length=2, max_length=50, description="Service Unit identifier or code")
    department_id: Optional[str] = Field(None, min_length=2, max_length=50, description="Department identifier or code")
    faculty_id: Optional[str] = Field(None, min_length=2, max_length=50, description="Faculty identifier or code")
    role_title: str = Field(..., min_length=2, max_length=100, description="Responsibility title, e.g. Lab Coordinator")
    status: ResponsibilityStatus = Field(ResponsibilityStatus.ACTIVE, description="ACTIVE or INACTIVE")

    @model_validator(mode="after")
    def require_organizational_target(self):
        if not (self.service_unit_id or self.department_id or self.faculty_id):
            raise ValueError("At least one of service_unit_id, department_id or faculty_id is required.")
        return self

class ResponsibilityUpdate(BaseModel):
    service_unit_id: Optional[str] = Field(None, min_length=2, max_length=50, description="New Service Unit identifier or code")
    department_id: Optional[str] = Field(None, min_length=2, max_length=50, description="New Department identifier or code")
    faculty_id: Optional[str] = Field(None, min_length=2, max_length=50, description="New Faculty identifier or code")
    role_title: Optional[str] = Field(None, min_length=2, max_length=100, description="Updated responsibility title")
    status: Optional[ResponsibilityStatus] = Field(None, description="ACTIVE or INACTIVE")

class ResponsibilityResponse(BaseModel):
    id: str
    user_id: str
    service_unit_id: Optional[str] = None
    service_unit_code: Optional[str] = None
    service_unit_name: Optional[str] = None
    department_id: Optional[str] = None
    department_code: Optional[str] = None
    department_name: Optional[str] = None
    faculty_id: Optional[str] = None
    faculty_code: Optional[str] = None
    faculty_name: Optional[str] = None
    role_title: str
    status: ResponsibilityStatus
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class ResponsibilitySingleResponse(BaseModel):
    success: bool = True
    data: ResponsibilityResponse

class ResponsibilityListResponse(BaseModel):
    success: bool = True
    data: List[ResponsibilityResponse]
