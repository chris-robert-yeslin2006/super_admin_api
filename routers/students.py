from fastapi import APIRouter
from database import supabase

router = APIRouter(prefix="/students", tags=["Students"])

@router.get("/list")
def list_students():
    response = supabase.table("students").select("*").execute()
    return {"students": response.data}