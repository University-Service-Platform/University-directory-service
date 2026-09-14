from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from datetime import datetime

class AffiliationBase(BaseModel):
    user_id: str = Field(..., min_length=2, max_length=50, description="User Identifier")
    department_id: str = Field(..., min_length=2, max_length=50, description="Department Identifier or Code")
    faculty_id: Optional[str] = Field(None, min_length=2, max_length=50, description="Optional Faculty Identifier or Code")

class AffiliationCreate(AffiliationBase):
    pass

class AffiliationUpdate(BaseModel):
    department_id: Optional[str] = Field(None, min_length=2, max_length=50, description="Updated Department Identifier or Code")
    faculty_id: Optional[str] = Field(None, min_length=2, max_length=50, description="Optional Updated Faculty Identifier or Code")

class AffiliationResponse(BaseModel):
    id: str
    user_id: str
    department_id: str
    department_name: Optional[str] = None
    department_code: Optional[str] = None
    faculty_id: str
    faculty_name: Optional[str] = None
    faculty_code: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class AffiliationSingleResponse(BaseModel):
    success: bool = True
    data: AffiliationResponse

class AffiliationListResponse(BaseModel):
    success: bool = True
    data: List[AffiliationResponse]
