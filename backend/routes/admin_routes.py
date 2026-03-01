"""
FocusFlow Admin Routes
Handles admin dashboard and user management endpoints
"""

from fastapi import APIRouter, HTTPException, status, Depends
from typing import List
from schemas import (
    AdminStatisticsResponse,
    UserStatisticsResponse,
    UserResponse,
    MessageResponse,
    UserSystemRoleUpdate
)
from auth import check_admin_role
from database import (
    db as supabase_db,
    get_all_users, 
    get_admin_statistics, 
    get_user_by_id,
    create_classroom
)
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["Admin"])

# ... (Previous endpoints)

@router.get("/classrooms")
async def get_all_admin_classrooms(current_user: dict = Depends(get_current_admin)):
    """
    Get all classrooms
    
    **Admin only**
    """
    try:
        classrooms = get_all_classrooms()
        return classrooms
    except Exception as e:
        logger.error(f"❌ Admin get classrooms error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch classrooms"
        )

@router.delete("/classrooms/{classroom_id}", response_model=MessageResponse)
async def delete_classroom_admin(
    classroom_id: int,
    current_user: dict = Depends(get_current_admin)
):
    """
    Delete a classroom
    
    **Admin only**
    """
    try:
        cls = get_classroom_by_id(classroom_id)
        if not cls:
            raise HTTPException(status_code=404, detail="Classroom not found")
            
        delete_classroom(classroom_id)
        logger.info(f"✅ Admin {current_user['username']} deleted classroom {classroom_id}")
        
        return MessageResponse(
            message="Classroom deleted",
            success=True
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Admin delete classroom error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete classroom"
        )


@router.put("/users/{user_id}/role", response_model=MessageResponse)
async def update_user_role_endpoint(
    user_id: int, 
    request: UserSystemRoleUpdate,
    current_user: dict = Depends(get_current_admin)
):
    """
    Update a user's system role
    
    **Admin only**
    """
    try:
        user = get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Prevent admin from removing their own admin status (safety check)
        if user['id'] == current_user['id'] and request.role != 'admin':
             raise HTTPException(status_code=400, detail="Cannot demote yourself. Create another admin first.")
             
        update_user_system_role(user_id, request.role.value)
        
        logger.info(f"✅ Admin {current_user['username']} updated user {user_id} role to {request.role}")
        
        return MessageResponse(
            message=f"User role updated to {request.role}",
            success=True
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Update user role error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user role"
        )


@router.delete("/users/{user_id}", response_model=MessageResponse)
async def delete_user_endpoint(
    user_id: int,
    current_user: dict = Depends(get_current_admin)
):
    """
    Delete a user
    
    **Admin only**
    """
    try:
        user = get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
            
        if user['id'] == current_user['id']:
             raise HTTPException(status_code=400, detail="Cannot delete yourself.")
             
        delete_user(user_id)
        
        logger.info(f"✅ Admin {current_user['username']} deleted user {user_id}")
        
        return MessageResponse(
            message="User deleted successfully",
            success=True
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Delete user error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete user"
        )

# ... (rest of endpoints)


@router.get("/users", response_model=List[UserResponse])
async def get_users(current_user: dict = Depends(get_current_admin)):
    """
    Get list of all registered students
    
    **Admin only**
    
    Returns list of all student users with basic information
    """
    try:
        users = get_all_users()
        
        user_responses = []
        for user in users:
            user_responses.append(UserResponse(**user))
        
        logger.info(f"✅ Admin {current_user['email']} retrieved {len(users)} users")
        
        return user_responses
        
    except Exception as e:
        logger.error(f"❌ Get users error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve users"
        )


@router.get("/statistics", response_model=AdminStatisticsResponse)
async def get_statistics(current_user: dict = Depends(get_current_admin)):
    """
    Get aggregated system statistics
    
    **Admin only**
    
    Returns:
    - Total number of students
    - Total number of sessions
    - Overall average focus score
    - Total study time across all users
    - Sessions with camera enabled
    - Most popular study technique
    - Most popular study mode
    """
    try:
        stats = get_admin_statistics()
        
        if not stats:
            # Return default stats if no data
            stats = {
                "total_students": 0,
                "total_sessions": 0,
                "overall_avg_focus_score": 0.0,
                "total_study_time_all_users": 0,
                "sessions_with_camera_enabled": 0,
                "most_popular_technique": None,
                "most_popular_mode": None
            }
        
        logger.info(f"✅ Admin {current_user['email']} retrieved statistics")
        
        return AdminStatisticsResponse(**stats)
        
    except Exception as e:
        logger.error(f"❌ Get statistics error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve statistics"
        )


@router.get("/user-statistics", response_model=List[UserStatisticsResponse])
async def get_user_statistics(current_user: dict = Depends(get_current_admin)):
    """
    Get detailed statistics for each user
    
    **Admin only**
    
    Returns per-user statistics:
    - Total sessions
    - Total study time
    - Average focus score
    - Total distractions
    - Average distractions per session
    - Most used technique
    - Sessions with camera enabled
    """
    try:
        user_stats = get_session_statistics()
        
        stats_responses = []
        for stats in user_stats:
            stats_responses.append(UserStatisticsResponse(**stats))
        
        logger.info(f"✅ Admin {current_user['email']} retrieved user statistics")
        
        return stats_responses
        
    except Exception as e:
        logger.error(f"❌ Get user statistics error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user statistics"
        )


@router.get("/dashboard-summary")
async def get_dashboard_summary(current_user: dict = Depends(get_current_admin)):
    """
    Get comprehensive dashboard summary
    
    **Admin only**
    
    Returns combined statistics for admin dashboard display
    """
    try:
        # Get overall statistics
        overall_stats = get_admin_statistics()
        
        # Get user statistics
        user_stats = get_session_statistics()
        
        # Get all users
        users = get_all_users()
        
        # Calculate additional metrics
        total_users = len(users)
        active_users = len([u for u in user_stats if u.get('total_sessions', 0) > 0])
        
        avg_sessions_per_user = (
            overall_stats.get('total_sessions', 0) / total_users 
            if total_users > 0 else 0
        )
        
        summary = {
            "overview": overall_stats,
            "total_users": total_users,
            "active_users": active_users,
            "avg_sessions_per_user": round(avg_sessions_per_user, 2),
            "user_statistics": user_stats[:10],  # Top 10 users
            "recent_users": users[:5]  # 5 most recent users
        }
        
        logger.info(f"✅ Admin {current_user['email']} retrieved dashboard summary")
        
        return summary
        
    except Exception as e:
        logger.error(f"❌ Get dashboard summary error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve dashboard summary"
        )


@router.get("/health", response_model=MessageResponse)
async def admin_health_check(current_user: dict = Depends(get_current_admin)):
    """
    Admin health check endpoint
    
    **Admin only**
    
    Verifies admin access and system status
    """
    return MessageResponse(
        message=f"Admin access verified for {current_user['username']}",
        success=True
    )
