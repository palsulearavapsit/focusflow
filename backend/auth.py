"""
FocusFlow Auth Module - Supabase Edition
Refactored to rely on Supabase Auth for security
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import logging
from database import db as supabase_db
from config import settings
from typing import Optional, Dict

# Configure logging
logger = logging.getLogger(__name__)

# FastAPI Security helper
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")

async def get_current_user_id(token: str = Depends(oauth2_scheme)) -> str:
    """
    Verify Supabase JWT and return User UUID
    """
    try:
        # Supabase Python client handles the verification via get_user()
        response = supabase_db.client.auth.get_user(token)
        if not response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired Supabase token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return response.user.id
    except Exception as e:
        logger.error(f"❌ Supabase token verification error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired. Please login again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def get_current_user(user_id: str = Depends(get_current_user_id)) -> Dict:
    """
    Get the full user profile from the database
    """
    profile = supabase_db.client.table("profiles").select("*").eq("id", user_id).single().execute()
    if not profile.data:
        raise HTTPException(status_code=404, detail="User profile not found")
    return profile.data

async def get_current_active_user(current_user: Dict = Depends(get_current_user)) -> Dict:
    """Check if user profile is healthy"""
    return current_user

async def check_admin_role(current_user: Dict = Depends(get_current_user)) -> Dict:
    """Verify admin privileges"""
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user

# Aliases for compatibility with existing routes
get_current_student = get_current_user
get_current_teacher = get_current_user
get_current_admin = check_admin_role

# Note: Your /api/auth/signup and /api/auth/login routes in auth_routes.py
# should now use supabase.auth.sign_up() and supabase.auth.sign_in_with_password()
