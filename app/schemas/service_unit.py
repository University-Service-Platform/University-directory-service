from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from datetime import datetime

class ServiceUnitBase(BaseModel):
    code: str = Field(..., min_length=2, max_length=20, description="Unique Service Unit Code, e.g. LIB")
    name: str = Field(..., min_length=2, max_length=150, description="Service Unit Name")
    description: Optional[str] = Field(None, max_length=255, description="Optional Description")

class ServiceUnitCreate(ServiceUnitBase):
    pass

class ServiceUnitUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=150, description="Updated Service Unit Name")
    description: Optional[str] = Field(None, max_length=255, description="Updated Description")
    code: Optional[str] = Field(None, min_length=2, max_length=20, description="Updated Service Unit Code")

class ServiceUnitResponse(ServiceUnitBase):
    id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ServiceUnitSingleResponse(BaseModel):
    success: bool = True
    data: ServiceUnitResponse

class ServiceUnitListResponse(BaseModel):
    success: bool = True
    data: List[ServiceUnitResponse]
