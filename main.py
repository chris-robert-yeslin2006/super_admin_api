from fastapi import FastAPI, HTTPException,Query
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client, Client
from dotenv import load_dotenv
from models import OrganizationCreate, AdminCreate,AdminUpdate
import os
from fastapi.responses import JSONResponse
from fastapi import Path
from fastapi import Body
from fastapi import Form
from auth_utils import create_access_token, verify_password
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

print("Supabase URL:", SUPABASE_URL)
print("Supabase KEY:", SUPABASE_KEY)

@app.post("/organization/add")
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
        "email": org.email
    }).execute()
    
    # Create auth record
    auth_response = supabase.table("auth").insert({
        "username": org.name,
        "email": org.email,
        "password": org.password,
        "role": "org"
    }).execute()
    
    return {"message": "Organization added", "data": org_response.data}

@app.get("/organization/list")
def list_organizations():
    response = supabase.table("organizations").select("*").execute()
    return {"organizations": response.data}

@app.post("/admin/add")
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

@app.get("/admin/list")
def list_admins(org_id: str = Query(default=None)):
    query = supabase.table("admins").select("id, name, contact, role, language, created_at, organizations(name)")

    if org_id:
        query = query.eq("org_id", org_id)
    
    response = query.execute()
    return {"admins": response.data}

@app.get("/analytics/students")
def get_students_for_analytics(org_id: str = Query(...), language: str = Query(...)):
    """
    Fetch students for a specific organization and language
    """
    response = supabase.table("students").select(
        "id, name, email, language, overall_mark, average_mark, recent_test_mark, "
        "fluency_mark, vocab_mark, sentence_mastery, pronunciation"
    ).eq("org_id", org_id).eq("language", language).execute()

    return {"students": response.data}

@app.get("/analytics/summary")
def get_summary_for_language(org_id: str = Query(...), language: str = Query(...)):
    """
    Provide summary statistics (like averages) for a given organization and language
    """
    response = supabase.table("students").select(
        "overall_mark, fluency_mark, vocab_mark, pronunciation"
    ).eq("org_id", org_id).eq("language", language).execute()

    data = response.data
    if not data:
        return {"summary": {}}

    # Compute averages
    total = len(data)
    summary = {
        "avg_overall": sum(s["overall_mark"] for s in data) / total,
        "avg_fluency": sum(s["fluency_mark"] for s in data) / total,
        "avg_vocab": sum(s["vocab_mark"] for s in data) / total,
        "avg_pronunciation": sum(s["pronunciation"] for s in data) / total,
    }

    return {"summary": summary}

@app.get("/analytics/language-detail")
def get_language_detail(org_id: str, language: str):
    students = supabase.table("students").select("*")\
        .eq("org_id", org_id).eq("language", language).execute().data

    if not students:
        return {"message": "No data", "total_students": 0}

    average = sum(s["overall_mark"] for s in students) / len(students)
    top_student = max(students, key=lambda s: s["overall_mark"])

    return {
        "language": language,
        "total_students": len(students),
        "average_mark": average,
        "top_student": {
            "name": top_student["name"],
            "overall_mark": top_student["overall_mark"]
        }
    }

@app.put("/organization/update/{org_id}")
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
        "email": updated_data.get("email", existing_org_data["email"])
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

@app.delete("/organization/delete/{org_id}")
def delete_organization(org_id: str = Path(..., description="The ID of the organization to delete")):
    # Get organization data first to get the email
    existing_org = supabase.table("organizations").select("*").eq("id", org_id).execute()
    if not existing_org.data:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    existing_org_data = existing_org.data[0]
    
    # Delete from auth table first
    supabase.table("auth").delete().eq("email", existing_org_data["email"]).execute()
    
    # Then delete from organizations table
    response = supabase.table("organizations").delete().eq("id", org_id).execute()
    
    return {"message": "Organization deleted", "data": response.data}


@app.post("/auth/login")
def login(email: str = Form(...), password: str = Form(...)):
    user_data = supabase.table("super_admins").select("*").eq("email", email).single().execute()

    if not user_data.data or not verify_password(password, user_data.data["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({"sub": user_data.data["email"]})
    return {"access_token": token, "token_type": "bearer"}

@app.put("/admin/update/{admin_id}")
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


# ---------------------
# DELETE ADMIN ENDPOINT
# ---------------------
@app.delete("/admin/delete/{admin_id}")
def delete_admin(admin_id: str):
    result = supabase.from_("admins").delete().eq("id", admin_id).execute()

    if result.error:
        raise HTTPException(status_code=500, detail="Failed to delete admin")

    return {"message": "Admin deleted successfully"}