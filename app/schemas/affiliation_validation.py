from pydantic import BaseModel
from typing import List

class OrganizationalUnitRef(BaseModel):
    id: str
    code: str
    name: str

class AffiliationMatch(BaseModel):
    affiliation_id: str
    department: OrganizationalUnitRef
    faculty: OrganizationalUnitRef

class UserAffiliationValidationData(BaseModel):
    user_id: str
    is_valid: bool
    affiliations: List[AffiliationMatch]

class UserAffiliationValidationResponse(BaseModel):
    success: bool = True
    data: UserAffiliationValidationData
