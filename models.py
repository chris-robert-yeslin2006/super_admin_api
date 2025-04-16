from pydantic import BaseModel
from typing import Optional

# -------- ORGANIZATION MODELS --------
class OrganizationBase(BaseModel):
    name: str
    head: str
    ambassador_name: str
    ambassador_contact: str
    contact: str
    email: str

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
    name: Optional[str]
    contact: Optional[str]
    role: Optional[str]
    language: Optional[str]
    email: Optional[str]
    password: Optional[str]
    org_name: Optional[str]  # Only if you allow updating org via name

class AdminOut(AdminBase):
    id: str
    org_id: str

    class Config:
        from_attributes = True
