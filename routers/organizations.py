from fastapi import APIRouter, HTTPException, Body, Path, Query
from typing import Optional
from models import OrganizationCreate
from database import supabase
from enum import Enum

router = APIRouter(prefix="/organization", tags=["Organizations"])

class OrganizationStatus(str, Enum):
    ONBOARD = "onboard"
    CONTACTED = "contacted"
    STANDBY = "standby"
    UNDER_VERIFICATION = "under verification"
    VERIFIED = "verified"

@router.post("/add")
def add_organization(org: OrganizationCreate):
    existing = supabase.table("organizations").select("*").eq("name", org.name).execute()
    if existing.data:
        raise HTTPException(status_code=400, detail="Organization already exists")
    
    # Check if email already exists in auth table
    existing_auth = supabase.table("auth").select("*").eq("email", org.email).execute()
    if existing_auth.data:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create organization record
    org_response = supabase.table("organizations").insert({
        "name": org.name,
        "head": org.head,
        "ambassador_name": org.ambassador_name,
        "ambassador_contact": org.ambassador_contact,
        "contact": org.contact,
        "email": org.email,
        "status": org.status
    }).execute()
    
    # Create auth record
    auth_response = supabase.table("auth").insert({
        "username": org.name,
        "email": org.email,
        "password": org.password,
        "role": "org"
    }).execute()
    
    return {"message": "Organization added", "data": org_response.data}

@router.get("/list")
def list_organizations():
    response = supabase.table("organizations").select("*").execute()
    return {"organizations": response.data}

@router.put("/update/{org_id}")
def update_organization(org_id: str, updated_data: dict = Body(...)):
    # Get existing organization data
    existing_org = supabase.table("organizations").select("*").eq("id", org_id).execute()
    if not existing_org.data:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    existing_org_data = existing_org.data[0]
    
    # Check if email is being updated and if it already exists
    if 'email' in updated_data and updated_data['email'] != existing_org_data['email']:
        email_check = supabase.table("auth").select("*").eq("email", updated_data['email']).execute()
        if email_check.data:
            raise HTTPException(status_code=400, detail="Email already registered")
    
    # Update organization record
    org_update_data = {
        "name": updated_data.get("name", existing_org_data["name"]),
        "head": updated_data.get("head", existing_org_data["head"]),
        "ambassador_name": updated_data.get("ambassador_name", existing_org_data["ambassador_name"]),
        "ambassador_contact": updated_data.get("ambassador_contact", existing_org_data["ambassador_contact"]),
        "contact": updated_data.get("contact", existing_org_data["contact"]),
        "email": updated_data.get("email", existing_org_data["email"]),
        "status": updated_data.get("status", existing_org_data.get("status", "onboard"))
    }
    
    org_response = supabase.table("organizations").update(org_update_data).eq("id", org_id).execute()
    
    # Update auth record if email or password changed
    auth_update_data = {}
    if 'email' in updated_data:
        auth_update_data["email"] = updated_data["email"]
    if 'password' in updated_data:
        auth_update_data["password"] = updated_data["password"]
    
    if auth_update_data:
        supabase.table("auth").update(auth_update_data).eq("email", existing_org_data["email"]).execute()
    
    return {"message": "Organization updated", "data": org_response.data}