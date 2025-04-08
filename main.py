from fastapi import FastAPI, HTTPException,Query
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client, Client
from dotenv import load_dotenv
from models import OrganizationCreate, AdminCreate
import os

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3001",],
    
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

@app.post("/organization/add")
def add_organization(org: OrganizationCreate):
    existing = supabase.table("organizations").select("*").eq("name", org.name).execute()
    if existing.data:
        raise HTTPException(status_code=400, detail="Organization already exists")

    response = supabase.table("organizations").insert({
        "name": org.name,
        "head": org.head,
        "ambassador_name": org.ambassador_name,
        "ambassador_contact": org.ambassador_contact,
        "contact": org.contact
    }).execute()

    return {"message": "Organization added", "data": response.data}

@app.get("/organization/list")
def list_organizations():
    response = supabase.table("organizations").select("*").execute()
    return {"organizations": response.data}

@app.post("/admin/add")
def add_admin(admin: AdminCreate):
    # Step 1: Lookup organization by name
    org_lookup = supabase.table("organizations").select("id").eq("name", admin.org_name).execute()

    if not org_lookup.data:
        raise HTTPException(status_code=404, detail="Organization not found")

    org_id = org_lookup.data[0]['id']

    # Step 2: Insert admin using resolved org_id
    response = supabase.table("admins").insert({
        "name": admin.name,
        "org_id": org_id,
        "contact": admin.contact,
        "role": admin.role,
        "language": admin.language
    }).execute()

    return {"message": "Admin added", "data": response.data}

@app.get("/admin/list")
def list_admins(org_id: str = Query(default=None)):
    query = supabase.table("admins").select("id, name, contact, role, language, created_at, organizations(name)")

    if org_id:
        query = query.eq("org_id", org_id)
    
    response = query.execute()
    return {"admins": response.data}

