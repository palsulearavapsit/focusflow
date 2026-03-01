"""
FocusFlow Admin Routes - Supabase Edition
"""

from fastapi import APIRouter, HTTPException, status, Depends
from typing import List
from schemas import (
    AdminStatisticsResponse,
    UserStatisticsResponse,
    UserBaseResponse,
    MessageResponse
)
from auth import get_current_admin
import database

router = APIRouter(prefix="/api/admin", tags=["Admin"])

@router.get("/statistics", response_model=AdminStatisticsResponse)
async def get_statistics(current_user: dict = Depends(get_current_admin)):
    """Get aggregated system statistics"""
    try:
        return database.get_admin_statistics()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve statistics: {e}")

@router.get("/users", response_model=List[UserBaseResponse])
async def get_users(current_user: dict = Depends(get_current_admin)):
    """Get list of all users"""
    try:
        response = database.db.client.table("profiles").select("*").execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve users: {e}")

@router.delete("/users/{user_id}", response_model=MessageResponse)
async def delete_user(user_id: str, current_user: dict = Depends(get_current_admin)):
    """Delete a user via Supabase management SDK and Auth (if service role allowed)"""
    try:
        # In Supabase version, we'll just delete the profile (CASCADE will delete other data)
        # Note: Auth user deletion usually requires service role key
        database.db.client.table("profiles").delete().eq("id", user_id).execute()
        return MessageResponse(message="User deleted successfully", success=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sessions")
async def get_all_sessions(current_user: dict = Depends(get_current_admin)):
    """Get all study sessions"""
    try:
        response = database.db.client.table("sessions").select("*, profiles(*)").order("timestamp", desc=True).limit(50).execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/classrooms")
async def get_all_classrooms(current_user: dict = Depends(get_current_admin)):
    """Get all classrooms"""
    try:
        response = database.db.client.table("classrooms").select("*, profiles(*)").execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
