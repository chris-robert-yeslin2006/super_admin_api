from fastapi import APIRouter, HTTPException, Body, Query
from models import AdminCreate, AdminUpdate
from database import supabase

router = APIRouter(prefix="/admin", tags=["Admins"])

@router.post("/add")
def add_admin(admin: AdminCreate):
    # Step 1: Check if email already exists in auth table
    existing_auth = supabase.table("auth").select("*").eq("email", admin.email).execute()
    if existing_auth.data:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Step 2: Lookup organization by name
    org_lookup = supabase.table("organizations").select("id").eq("name", admin.org_name).execute()
    if not org_lookup.data:
        raise HTTPException(status_code=404, detail="Organization not found")
    org_id = org_lookup.data[0]['id']

    # Step 3: Insert admin record
    admin_response = supabase.table("admins").insert({
        "name": admin.name,
        "org_id": org_id,
        "contact": admin.contact,
        "role": admin.role,
        "language": admin.language,
        "email": admin.email  # Store email in admins table
    }).execute()

    # Step 4: Create auth record
    auth_response = supabase.table("auth").insert({
        "username": admin.name,
        "email": admin.email,
        "password": admin.password,
        "role": "admin"
    }).execute()

    return {"message": "Admin added", "data": admin_response.data}

@router.get("/list")
def list_admins(org_id: str = Query(default=None)):
    query = supabase.table("admins").select("id, name, contact, role, language, created_at, organizations(name)")

    if org_id:
        query = query.eq("org_id", org_id)
    
    response = query.execute()
    return {"admins": response.data}

@router.put("/update/{admin_id}")
def update_admin(admin_id: str, updated_data: dict = Body(...)):
    # Get current admin data
    current_admin = supabase.table("admins").select("*").eq("id", admin_id).execute()
    if not current_admin.data:
        raise HTTPException(status_code=404, detail="Admin not found")
    
    current_email = current_admin.data[0]['email']
    
    # Check if email is being updated and if it's already taken
    if 'email' in updated_data and updated_data['email'] != current_email:
        existing = supabase.table("admins").select("*").eq("email", updated_data['email']).neq("id", admin_id).execute()
        if existing.data:
            raise HTTPException(status_code=400, detail="Email already in use")

    # Update admin record
    admin_response = supabase.table("admins").update(updated_data).eq("id", admin_id).execute()
    
    # Update auth table if email or password changed
    auth_updates = {}
    if 'email' in updated_data:
        auth_updates['email'] = updated_data['email']
    if 'password' in updated_data:
        auth_updates['password'] = updated_data['password']
    
    if auth_updates:
        supabase.table("auth").update(auth_updates).eq("email", current_email).execute()
    
    return {"message": "Admin updated", "data": admin_response.data}

@router.delete("/delete/{admin_id}")
def delete_admin(admin_id: str):
    result = supabase.from_("admins").delete().eq("id", admin_id).execute()

    if result.error:
        raise HTTPException(status_code=500, detail="Failed to delete admin")

    return {"message": "Admin deleted successfully"}