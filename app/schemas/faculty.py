from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from datetime import datetime

class FacultyValidationData(BaseModel):
    faculty_id: str
    code: str
    name: str
    is_valid: bool = True

    model_config = ConfigDict(from_attributes=True)

class FacultyValidationResponse(BaseModel):
    success: bool = True
    data: FacultyValidationData

class FacultyBase(BaseModel):
    code: str = Field(..., min_length=2, max_length=20, description="Unique Faculty Code, e.g. FSC")
    name: str = Field(..., min_length=2, max_length=150, description="Faculty Name")
    description: Optional[str] = Field(None, max_length=255, description="Optional Description")

class FacultyCreate(FacultyBase):
    pass

class FacultyUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=150, description="Updated Faculty Name")
    description: Optional[str] = Field(None, max_length=255, description="Updated Description")
    code: Optional[str] = Field(None, min_length=2, max_length=20, description="Updated Faculty Code")

class FacultyResponse(FacultyBase):
    id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class FacultySingleResponse(BaseModel):
    success: bool = True
    data: FacultyResponse

class FacultyListResponse(BaseModel):
    success: bool = True
    data: List[FacultyResponse]
