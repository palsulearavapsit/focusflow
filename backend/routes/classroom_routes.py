
"""
FocusFlow Classroom Routes
Handles classroom creation, joining, and statistics
"""

from datetime import datetime
from fastapi import APIRouter, HTTPException, status, Depends
from typing import List
import string
import random
import logging

from schemas import (
    ClassroomCreateRequest,
    JoinClassroomRequest,
    ClassroomResponse,
    ClassroomDetailsResponse,
    MessageResponse,
    UpdateRoleRequest
)
from auth import get_current_user
from database import db as supabase_db
import database as db_helpers

logger = logging.getLogger(__name__)




router = APIRouter(prefix="/api/classrooms", tags=["Classrooms"])


def generate_classroom_code():
    """Generate a random 10-character alphanumeric code"""
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choices(chars, k=10))


@router.post("/create", response_model=ClassroomResponse)
async def create_new_classroom(
    request: ClassroomCreateRequest,
    current_user: dict = Depends(get_current_teacher)
):
    """
    Create a new classroom
    
    **Teacher only**
    """
    try:
        # Generate unique code
        code = generate_classroom_code()
        
        # Simple collision check logic could be added here, but 36^10 is huge space.
        # We rely on DB unique constraint to fail if collision happens (extremely rare)
        
        classroom_id = db.create_classroom(request.name, code, current_user['id'])
        
        logger.info(f"✅ Teacher {current_user['username']} created classroom '{request.name}' ({code})")
        
        return ClassroomResponse(
            id=classroom_id,
            name=request.name,
            code=code,
            teacher_id=current_user['id'],
            created_at=datetime.now(),
            student_count=0
        )
        
    except Exception as e:
        logger.error(f"❌ Create classroom error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create classroom"
        )


@router.get("/{classroom_id}/my-sessions")
async def get_my_classroom_sessions(
    classroom_id: int,
    current_user: dict = Depends(get_current_student)
):
    """
    Get all sessions for the current student in a specific classroom
    
    **Student only**
    """
    try:
        if not db.is_student_in_classroom(classroom_id, current_user['id']):
            raise HTTPException(status_code=404, detail="You are not in this classroom")
            
        sessions = db.get_student_sessions_for_classroom(classroom_id, current_user['id'])
        return sessions
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Get my sessions error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve sessions"
        )


@router.post("/join", response_model=MessageResponse)
async def join_classroom(
    request: JoinClassroomRequest,
    current_user: dict = Depends(get_current_student)
):
    """
    Join a classroom using a code
    
    **Student only**
    """
    try:
        classroom = db.get_classroom_by_code(request.code)
        
        if not classroom:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Classroom code not found"
            )
            
        if db.is_student_in_classroom(classroom['id'], current_user['id']):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You are already in this classroom"
            )
            
        db.add_student_to_classroom(classroom['id'], current_user['id'])
        
        logger.info(f"✅ Student {current_user['username']} joined classroom '{classroom['name']}'")
        
        return MessageResponse(
            message=f"Successfully joined classroom: {classroom['name']}",
            success=True
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Join classroom error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to join classroom"
        )


@router.get("/teacher/list", response_model=List[ClassroomResponse])
async def list_teacher_classrooms(
    current_user: dict = Depends(get_current_teacher)
):
    """
    List all classrooms created by the teacher
    
    **Teacher only**
    """
    try:
        return db.get_teacher_classrooms(current_user['id'])
    except Exception as e:
        logger.error(f"❌ List teacher classrooms error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve classrooms"
        )


@router.get("/teacher/students")
async def get_all_my_students(current_user: dict = Depends(get_current_teacher)):
    """
    Get all students from all classrooms owned by the teacher
    
    **Teacher only**
    """
    try:
        return db.get_all_teacher_students(current_user['id'])
    except Exception as e:
        logger.error(f"❌ Get all teacher students error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve students"
        )


@router.get("/student/list", response_model=List[ClassroomResponse])
async def list_student_classrooms(
    current_user: dict = Depends(get_current_student)
):
    """
    List all classrooms the student has joined
    
    **Student only**
    """
    try:
        return db.get_student_classrooms(current_user['id'])
    except Exception as e:
        logger.error(f"❌ List student classrooms error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve classrooms"
        )


@router.get("/{classroom_id}/students/{student_id}/sessions")
async def get_classroom_student_sessions(
    classroom_id: int,
    student_id: int,
    current_user: dict = Depends(get_current_teacher)
):
    """
    Get all sessions for a specific student in a classroom
    
    **Teacher only**
    """
    try:
        classroom = db.get_classroom_by_id(classroom_id)
        if not classroom:
            raise HTTPException(status_code=404, detail="Classroom not found")
            
        if classroom['teacher_id'] != current_user['id']:
            raise HTTPException(status_code=403, detail="Not authorized to view this classroom")
            
        if not db.is_student_in_classroom(classroom_id, student_id):
            raise HTTPException(status_code=404, detail="Student not found in this classroom")
            
        sessions = db.get_student_sessions_for_classroom(classroom_id, student_id)
        return sessions
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Get student sessions error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve student sessions"
        )


@router.get("/{classroom_id}", response_model=ClassroomDetailsResponse)
async def get_classroom_details(
    classroom_id: int,
    current_user: dict = Depends(get_current_teacher)
):
    """
    Get detailed classroom stats
    
    **Teacher only** (Must be the owner of the classroom)
    """
    try:
        classroom = db.get_classroom_by_id(classroom_id)
        
        if not classroom:
            raise HTTPException(status_code=404, detail="Classroom not found")
            
        if classroom['teacher_id'] != current_user['id']:
            raise HTTPException(status_code=403, detail="Not authorized to view this classroom")
            
        students_stats = db.get_classroom_students_stats(classroom_id)
        
        return ClassroomDetailsResponse(
            classroom=ClassroomResponse(**classroom),
            students=students_stats
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Get classroom details error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve classroom details"
        )


@router.delete("/{classroom_id}", response_model=MessageResponse)
async def delete_classroom_endpoint(
    classroom_id: int,
    current_user: dict = Depends(get_current_teacher)
):
    """
    Delete a classroom
    
    **Teacher only**
    """
    try:
        classroom = db.get_classroom_by_id(classroom_id)
        if not classroom:
            raise HTTPException(status_code=404, detail="Classroom not found")
            
        if classroom['teacher_id'] != current_user['id']:
            raise HTTPException(status_code=403, detail="Not authorized to delete this classroom")
            
        db.delete_classroom(classroom_id)
        
        logger.info(f"✅ Teacher {current_user['username']} deleted classroom {classroom_id}")
        
        return MessageResponse(
            message="Classroom deleted successfully",
            success=True
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Delete classroom error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete classroom"
        )


@router.delete("/{classroom_id}/students/{student_id}", response_model=MessageResponse)
async def remove_student_endpoint(
    classroom_id: int,
    student_id: int,
    current_user: dict = Depends(get_current_teacher)
):
    """
    Remove a student from a classroom
    
    **Teacher only**
    """
    try:
        classroom = db.get_classroom_by_id(classroom_id)
        if not classroom:
            raise HTTPException(status_code=404, detail="Classroom not found")
            
        if classroom['teacher_id'] != current_user['id']:
            raise HTTPException(status_code=403, detail="Not authorized to manage this classroom")
            
        if not db.is_student_in_classroom(classroom_id, student_id):
            raise HTTPException(status_code=404, detail="Student not found in this classroom")
            
        db.remove_student_from_classroom(classroom_id, student_id)
        
        logger.info(f"✅ Teacher {current_user['username']} removed student {student_id} from classroom {classroom_id}")
        
        return MessageResponse(
            message="Student removed successfully",
            success=True
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Remove student error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove student"
        )


@router.delete("/{classroom_id}/leave", response_model=MessageResponse)
async def leave_classroom_endpoint(
    classroom_id: int,
    current_user: dict = Depends(get_current_student)
):
    """
    Leave a classroom
    
    **Student only**
    """
    try:
        if not db.is_student_in_classroom(classroom_id, current_user['id']):
            raise HTTPException(status_code=404, detail="You are not in this classroom")
            
        db.leave_classroom(classroom_id, current_user['id'])
        
        logger.info(f"✅ Student {current_user['username']} left classroom {classroom_id}")
        
        return MessageResponse(
            message="Successfully left the classroom",
            success=True
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Leave classroom error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to leave classroom"
        )


@router.put("/{classroom_id}/students/{student_id}/role", response_model=MessageResponse)
async def update_student_role_endpoint(
    classroom_id: int,
    student_id: int,
    request: UpdateRoleRequest,
    current_user: dict = Depends(get_current_teacher)
):
    """
    Update a student's role in the classroom (e.g. promote to representative)
    
    **Teacher only**
    """
    try:
        classroom = db.get_classroom_by_id(classroom_id)
        if not classroom:
            raise HTTPException(status_code=404, detail="Classroom not found")
            
        if classroom['teacher_id'] != current_user['id']:
            raise HTTPException(status_code=403, detail="Not authorized to manage this classroom")
            
        if not db.is_student_in_classroom(classroom_id, student_id):
            raise HTTPException(status_code=404, detail="Student not found in this classroom")
            
        # Check if trying to promote to representative when one already exists
        if request.role == 'representative':
            existing_rep_id = db.get_classroom_representative(classroom_id)
            if existing_rep_id and existing_rep_id != student_id:
                # Demote the previous representative to student
                db.update_student_role(classroom_id, existing_rep_id, 'student')
                logger.info(f"ℹ️ Automatically demoted previous representative {existing_rep_id} to student")
            
        db.update_student_role(classroom_id, student_id, request.role)
        
        logger.info(f"✅ Teacher {current_user['username']} updated student {student_id} role to {request.role}")
        
        return MessageResponse(
            message=f"Student role updated to {request.role}",
            success=True
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Update role error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update student role"
        )


