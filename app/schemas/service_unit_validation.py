from pydantic import BaseModel, ConfigDict
from typing import Optional

class ServiceUnitValidationData(BaseModel):
    unit_id: str
    code: str
    name: str
    description: Optional[str] = None
    is_valid: bool = True

    model_config = ConfigDict(from_attributes=True)

class ServiceUnitValidationResponse(BaseModel):
    success: bool = True
    data: ServiceUnitValidationData
