from pydantic import BaseModel
from typing import Optional
from enum import Enum

class OrganizationStatus(str, Enum):
    ONBOARD = "onboard"
    CONTACTED = "contacted"
    STANDBY = "standby"
    UNDER_VERIFICATION = "under verification"
    VERIFIED = "verified"

# -------- ORGANIZATION MODELS --------
class OrganizationBase(BaseModel):
    name: str
    head: str
    ambassador_name: str
    ambassador_contact: str
    contact: str
    email: str
    status: OrganizationStatus = OrganizationStatus.ONBOARD

class OrganizationCreate(OrganizationBase):
    password: str

class OrganizationUpdate(BaseModel):
    name: Optional[str] = None
    head: Optional[str] = None
    ambassador_name: Optional[str] = None
    ambassador_contact: Optional[str] = None
    contact: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None
    status: Optional[OrganizationStatus] = None

class OrganizationOut(OrganizationBase):
    id: str
    
    class Config:
        from_attributes = True

# -------- ADMIN MODELS --------
class AdminBase(BaseModel):
    name: str
    role: str
    contact: str
    language: str
    email: str

class AdminCreate(AdminBase):
    org_name: str  # Frontend provides org_name, backend converts to org_id
    password: str

class AdminUpdate(BaseModel):
    name: Optional[str] = None
    contact: Optional[str] = None
    role: Optional[str] = None
    language: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None
    org_name: Optional[str] = None  # Only if you allow updating org via name

class AdminOut(AdminBase):
    id: str
    org_id: str
    
    class Config:
        from_attributes = True