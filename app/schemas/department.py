from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from datetime import datetime

class DepartmentBase(BaseModel):
    code: str = Field(..., min_length=2, max_length=20, description="Unique Department Code, e.g. DEPT-CS")
    name: str = Field(..., min_length=2, max_length=100, description="Department Name")
    faculty_id: str = Field(..., min_length=2, max_length=50, description="Parent Faculty Identifier")

class DepartmentCreate(DepartmentBase):
    pass

class DepartmentUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100, description="Updated Department Name")
    code: Optional[str] = Field(None, min_length=2, max_length=20, description="Updated Department Code")
    faculty_id: Optional[str] = Field(None, min_length=2, max_length=50, description="Updated Faculty Identifier")

class DepartmentResponse(DepartmentBase):
    id: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class DepartmentSingleResponse(BaseModel):
    success: bool = True
    data: DepartmentResponse

class DepartmentListResponse(BaseModel):
    success: bool = True
    data: List[DepartmentResponse]
