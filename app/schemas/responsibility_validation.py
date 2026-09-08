from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from app.models.service_responsibility import ResponsibilityStatus

class ResponsibilityRecordData(BaseModel):
    responsibility_id: str
    user_id: str
    service_unit_id: Optional[str] = None
    service_unit_name: Optional[str] = None
    department_id: Optional[str] = None
    department_name: Optional[str] = None
    faculty_id: Optional[str] = None
    faculty_name: Optional[str] = None
    role_title: str
    status: ResponsibilityStatus

    model_config = ConfigDict(from_attributes=True)

class UserResponsibilityValidationData(BaseModel):
    user_id: str
    is_valid: bool
    responsibilities: List[ResponsibilityRecordData]

class UserResponsibilityValidationResponse(BaseModel):
    success: bool = True
    data: UserResponsibilityValidationData
