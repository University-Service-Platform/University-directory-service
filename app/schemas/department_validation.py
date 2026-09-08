from pydantic import BaseModel, ConfigDict
from typing import Optional

class DepartmentValidationData(BaseModel):
    department_id: str
    code: str
    name: str
    faculty_id: str
    faculty_name: str
    is_valid: bool = True

    model_config = ConfigDict(from_attributes=True)

class DepartmentValidationResponse(BaseModel):
    success: bool = True
    data: DepartmentValidationData
