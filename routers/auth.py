from fastapi import APIRouter, Form, HTTPException
from auth_utils import create_access_token, verify_password
from database import supabase

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/login")
def login(email: str = Form(...), password: str = Form(...)):
    user_data = supabase.table("super_admins").select("*").eq("email", email).single().execute()

    if not user_data.data or not verify_password(password, user_data.data["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({"sub": user_data.data["email"]})
    return {"access_token": token, "token_type": "bearer"}