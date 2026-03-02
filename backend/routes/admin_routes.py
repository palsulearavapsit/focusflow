"""
FocusFlow Admin Routes - MySQL Edition
"""

from fastapi import APIRouter, HTTPException, status, Depends
from typing import List
from schemas import (
    AdminStatisticsResponse,
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
        users = database.get_all_users()
        # Convert id to str for schema compatibility
        for u in users:
            u["id"] = str(u["id"])
        return users
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve users: {e}")


@router.delete("/users/{user_id}", response_model=MessageResponse)
async def delete_user(user_id: int, current_user: dict = Depends(get_current_admin)):
    """Delete a user"""
    try:
        database.delete_user(user_id)
        return MessageResponse(message="User deleted successfully", success=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions")
async def get_all_sessions(current_user: dict = Depends(get_current_admin)):
    """Get all study sessions"""
    try:
        sessions = database.get_all_sessions(limit=50)
        for s in sessions:
            s["id"] = str(s["id"])
            s["user_id"] = str(s["user_id"])
        return sessions
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/classrooms")
async def get_all_classrooms(current_user: dict = Depends(get_current_admin)):
    """Get all classrooms"""
    try:
        classrooms = database.get_all_classrooms()
        for c in classrooms:
            c["id"] = str(c["id"])
            c["teacher_id"] = str(c["teacher_id"])
        return classrooms
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
@router.get("/dashboard-summary")
async def get_dashboard_summary(current_user: dict = Depends(get_current_admin)):
    """Get summarized dashboard data for admin"""
    try:
        stats = database.get_admin_statistics()
        # Count all users
        conn = database.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]
        cursor.close(); conn.close()
        
        return {
            "total_users": total_users,
            "overview": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/user-statistics")
async def get_all_user_stats(current_user: dict = Depends(get_current_admin)):
    """Get detailed statistics for all users"""
    try:
        return database.get_all_user_statistics()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/users/{user_id}/role")
async def update_user_role(
    user_id: int, 
    request: dict, # Using dict to avoid schema mismatch for now, or use UserSystemRoleUpdate if available
    current_user: dict = Depends(get_current_admin)
):
    """Update a user's system role"""
    try:
        role = request.get("role")
        if not role:
            raise HTTPException(status_code=400, detail="Role is required")
        database.update_user_system_role(user_id, role)
        return {"success": True, "message": f"User role updated to {role}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
@router.delete("/classrooms/{classroom_id}", response_model=MessageResponse)
async def delete_classroom(classroom_id: int, current_user: dict = Depends(get_current_admin)):
    """Delete a classroom (admin)"""
    try:
        database.delete_classroom(classroom_id)
        return MessageResponse(message="Classroom deleted successfully", success=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
