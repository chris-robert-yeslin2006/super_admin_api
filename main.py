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
from enum import Enum
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import Query

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

# @app.post("/organization/add")
# def add_organization(org: OrganizationCreate):
#     existing = supabase.table("organizations").select("*").eq("name", org.name).execute()
#     if existing.data:
#         raise HTTPException(status_code=400, detail="Organization already exists")
    
#     # Check if email already exists in auth table
#     existing_auth = supabase.table("auth").select("*").eq("email", org.email).execute()
#     if existing_auth.data:
#         raise HTTPException(status_code=400, detail="Email already registered")
    
#     # Create organization record
#     org_response = supabase.table("organizations").insert({
#         "name": org.name,
#         "head": org.head,
#         "ambassador_name": org.ambassador_name,
#         "ambassador_contact": org.ambassador_contact,
#         "contact": org.contact,
#         "email": org.email
#     }).execute()
    
#     # Create auth record
#     auth_response = supabase.table("auth").insert({
#         "username": org.name,
#         "email": org.email,
#         "password": org.password,
#         "role": "org"
#     }).execute()
    
#     return {"message": "Organization added", "data": org_response.data}

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
def get_students_for_analytics(
    org_id: Optional[str] = Query(None),
    language: Optional[str] = Query(None)
):
    """
    Fetch students optionally filtered by organization and language
    """
    query = supabase.table("students").select(
        "id, name, email, language, overall_mark, average_mark, recent_test_mark, "
        "fluency_mark, vocab_mark, sentence_mastery, pronunciation"
    )

    if org_id:
        query = query.eq("org_id", org_id)
    if language:
        query = query.eq("language", language)

    response = query.execute()

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

# @app.put("/organization/update/{org_id}")
# def update_organization(org_id: str, updated_data: dict = Body(...)):
#     # Get existing organization data
#     existing_org = supabase.table("organizations").select("*").eq("id", org_id).execute()
#     if not existing_org.data:
#         raise HTTPException(status_code=404, detail="Organization not found")
    
#     existing_org_data = existing_org.data[0]
    
#     # Check if email is being updated and if it already exists
#     if 'email' in updated_data and updated_data['email'] != existing_org_data['email']:
#         email_check = supabase.table("auth").select("*").eq("email", updated_data['email']).execute()
#         if email_check.data:
#             raise HTTPException(status_code=400, detail="Email already registered")
    
#     # Update organization record
#     org_update_data = {
#         "name": updated_data.get("name", existing_org_data["name"]),
#         "head": updated_data.get("head", existing_org_data["head"]),
#         "ambassador_name": updated_data.get("ambassador_name", existing_org_data["ambassador_name"]),
#         "ambassador_contact": updated_data.get("ambassador_contact", existing_org_data["ambassador_contact"]),
#         "contact": updated_data.get("contact", existing_org_data["contact"]),
#         "email": updated_data.get("email", existing_org_data["email"])
#     }
    
#     org_response = supabase.table("organizations").update(org_update_data).eq("id", org_id).execute()
    
#     # Update auth record if email or password changed
#     auth_update_data = {}
#     if 'email' in updated_data:
#         auth_update_data["email"] = updated_data["email"]
#     if 'password' in updated_data:
#         auth_update_data["password"] = updated_data["password"]
    
#     if auth_update_data:
#         supabase.table("auth").update(auth_update_data).eq("email", existing_org_data["email"]).execute()
    
#     return {"message": "Organization updated", "data": org_response.data}

# @app.delete("/organization/delete/{org_id}")
# def delete_organization(org_id: str = Path(..., description="The ID of the organization to delete")):
#     # Get organization data first to get the email
#     existing_org = supabase.table("organizations").select("*").eq("id", org_id).execute()
#     if not existing_org.data:
#         raise HTTPException(status_code=404, detail="Organization not found")
    
#     existing_org_data = existing_org.data[0]
    
#     # Delete from auth table first
#     supabase.table("auth").delete().eq("email", existing_org_data["email"]).execute()
    
#     # Then delete from organizations table
#     response = supabase.table("organizations").delete().eq("id", org_id).execute()
    
#     return {"message": "Organization deleted", "data": response.data}


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

class OrganizationStatus(str, Enum):
    ONBOARD = "onboard"
    CONTACTED = "contacted"
    STANDBY = "standby"
    UNDER_VERIFICATION = "under verification"
    VERIFIED = "verified"

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

@app.get("/students/list")
def list_students():
    response = supabase.table("students").select("*").execute()
    return {"students": response.data}

@app.get("/analytics/organizations/status")
def get_organizations_by_status(
    timeframe: str = Query("7days", description="Time period: 7days, 15days, 1month, quarter"),
    start_date: Optional[str] = Query(None, description="Optional custom start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Optional custom end date (YYYY-MM-DD)")
):
    """
    Get organization counts grouped by status for the specified timeframe.
    """
    # Calculate date range based on timeframe or custom dates
    today = datetime.now()
    
    if start_date and end_date:
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
    else:
        # Set date range based on timeframe parameter
        if timeframe == "7days":
            start = today - timedelta(days=7)
        elif timeframe == "15days":
            start = today - timedelta(days=15)
        elif timeframe == "1month":
            start = today - timedelta(days=30)
        elif timeframe == "quarter":
            start = today - timedelta(days=90)
        else:
            start = today - timedelta(days=7)  # Default to 7 days
        end = today
    
    # Convert to string format that Supabase expects
    start_str = start.strftime("%Y-%m-%d")
    end_str = end.strftime("%Y-%m-%d")
    
    # Query organizations created within the date range
    query = supabase.table("organizations") \
        .select("id, name, status, created_at") \
        .gte("created_at", start_str) \
        .lte("created_at", end_str + "T23:59:59")
    
    response = query.execute()
    
    if not response.data:
        return {"data": [], "timeframe": timeframe}
    
    # Format response data for the chart
    result = {
        "data": response.data,
        "timeframe": timeframe,
        "date_range": {
            "start": start_str,
            "end": end_str
        }
    }
    
    return result

@app.get("/analytics/organizations/timeline")
def get_organizations_timeline(
    timeframe: str = Query("7days", description="Time period: 7days, 15days, 1month, quarter, halfyear, year")
):
    """
    Get organization counts over time, formatted for timeline charts.
    """
    # Map DB status to chart keys
    status_key_map = {
        "onboard": "onboarded",
        "contacted": "contacted",
        "standby": "standby",
        "under verification": "verification"
    }

    today = datetime.now()
    
    if timeframe == "7days":
        start_date = today - timedelta(days=7)
        group_by = "day"
    elif timeframe == "15days":
        start_date = today - timedelta(days=15)
        group_by = "day"
    elif timeframe == "1month":
        start_date = today - timedelta(days=30)
        group_by = "week"
    elif timeframe == "quarter":
        start_date = today - timedelta(days=90)
        group_by = "month"
    elif timeframe == "halfyear":
        start_date = today - timedelta(days=180)
        group_by = "month"
    elif timeframe == "year":
        start_date = today - timedelta(days=365)
        group_by = "month"
    else:
        start_date = today - timedelta(days=7)
        group_by = "day"

    start_str = start_date.strftime("%Y-%m-%d")

    response = supabase.table("organizations") \
        .select("id, name, status, created_at") \
        .gte("created_at", start_str) \
        .order("created_at") \
        .execute()
    
    organizations = response.data
    result = []

    if group_by == "day":
        date_format = "%Y-%m-%d"
        date_label_format = "%b %d"

        date_counts = {}
        current_date = start_date
        while current_date <= today:
            date_str = current_date.strftime(date_format)
            date_counts[date_str] = {
                "date": date_str,
                "label": current_date.strftime(date_label_format),
                "onboarded": 0,
                "contacted": 0,
                "standby": 0,
                "verification": 0
            }
            current_date += timedelta(days=1)

        for org in organizations:
            org_date = datetime.fromisoformat(org["created_at"].replace("Z", "+00:00")).strftime(date_format)
            status = org.get("status", "onboard")
            mapped_status = status_key_map.get(status)

            if mapped_status and mapped_status in date_counts[org_date]:
                date_counts[org_date][mapped_status] += 1

        result = list(date_counts.values())

    elif group_by == "week":
        weeks = []
        week_start = start_date
        while week_start <= today:
            week_end = week_start + timedelta(days=6)
            if week_end > today:
                week_end = today
            week_label = f"Week {len(weeks) + 1}"
            weeks.append({
                "start": week_start,
                "end": week_end,
                "label": week_label,
                "onboarded": 0,
                "contacted": 0,
                "standby": 0,
                "verification": 0
            })
            week_start = week_end + timedelta(days=1)

        for org in organizations:
            org_date = datetime.fromisoformat(org["created_at"].replace("Z", "+00:00"))
            status = org.get("status", "onboard")
            mapped_status = status_key_map.get(status)

            for week in weeks:
                if week["start"] <= org_date <= week["end"]:
                    if mapped_status and mapped_status in week:
                        week[mapped_status] += 1
                    break

        result = [
            {
                "name": week["label"],
                "onboarded": week["onboarded"],
                "contacted": week["contacted"],
                "standby": week["standby"],
                "verification": week["verification"]
            }
            for week in weeks
        ]

    elif group_by == "month":
        months = []
        current_month = datetime(start_date.year, start_date.month, 1)

        while current_month <= today:
            next_month = datetime(
                current_month.year + (1 if current_month.month == 12 else 0),
                1 if current_month.month == 12 else current_month.month + 1,
                1
            )
            month_label = current_month.strftime("%b")
            months.append({
                "start": current_month,
                "end": next_month - timedelta(days=1),
                "label": month_label,
                "onboarded": 0,
                "contacted": 0,
                "standby": 0,
                "verification": 0
            })
            current_month = next_month

        for org in organizations:
            org_date = datetime.fromisoformat(org["created_at"].replace("Z", "+00:00"))
            status = org.get("status", "onboard")
            mapped_status = status_key_map.get(status)

            for month in months:
                if month["start"] <= org_date <= month["end"]:
                    if mapped_status and mapped_status in month:
                        month[mapped_status] += 1
                    break

        result = [
            {
                "name": month["label"],
                "onboarded": month["onboarded"],
                "contacted": month["contacted"],
                "standby": month["standby"],
                "verification": month["verification"]
            }
            for month in months
        ]

    return {
        "data": result,
        "timeframe": timeframe,
        "group_by": group_by
    }

# You can also add a student analytics timeline endpoint if needed
@app.get("/analytics/students/timeline")
def get_students_timeline(
    timeframe: str = Query("7days", description="Time period: 7days, 15days, 1month, quarter"),
    language: Optional[str] = Query(None, description="Filter by language"),
    org_id: Optional[str] = Query(None, description="Filter by organization ID")
):
    """
    Get student counts over time, formatted for timeline charts.
    """
    # Calculate start date based on timeframe
    today = datetime.now()
    
    if timeframe == "7days":
        start_date = today - timedelta(days=7)
    elif timeframe == "15days":
        start_date = today - timedelta(days=15)
    elif timeframe == "1month":
        start_date = today - timedelta(days=30)
    elif timeframe == "quarter":
        start_date = today - timedelta(days=90)
    else:
        start_date = today - timedelta(days=7)
    
    # Format start date for Supabase query
    start_str = start_date.strftime("%Y-%m-%d")
    
    # Build the query
    query = supabase.table("students").select("id, name, language, created_at, org_id").gte("created_at", start_str)
    
    # Add filters if provided
    if language:
        query = query.eq("language", language)
    if org_id:
        query = query.eq("org_id", org_id)
    
    response = query.execute()
    students = response.data
    
    # Format data by day
    date_format = "%Y-%m-%d"
    date_label_format = "%b %d"  # e.g., "Jan 01"
    
    # Create a dictionary to store counts by date
    date_counts = {}
    
    # Initialize all dates in the range
    current_date = start_date
    while current_date <= today:
        date_str = current_date.strftime(date_format)
        date_counts[date_str] = {
            "date": date_str,
            "label": current_date.strftime(date_label_format),
            "count": 0
        }
        current_date += timedelta(days=1)
    
    # Count students by date
    for student in students:
        student_date = datetime.fromisoformat(student["created_at"].replace("Z", "+00:00")).strftime(date_format)
        if student_date in date_counts:
            date_counts[student_date]["count"] += 1
    
    # Convert to list for the response
    result = list(date_counts.values())
    
    return {
        "data": result,
        "timeframe": timeframe,
        "filters": {
            "language": language,
            "org_id": org_id
        }
    }