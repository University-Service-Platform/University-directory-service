from pydantic import BaseModel, ConfigDict
from typing import Optional

class FacultyValidationData(BaseModel):
    faculty_id: str
    code: str
    name: str
    is_valid: bool = True

    model_config = ConfigDict(from_attributes=True)

class FacultyValidationResponse(BaseModel):
    success: bool = True
    data: FacultyValidationData
