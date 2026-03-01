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
from auth import get_current_teacher, get_current_student, get_current_user
import database

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
    """Create a new classroom"""
    try:
        code = generate_classroom_code()
        classroom_result = database.create_classroom(request.name, code, current_user['id'])
        
        return ClassroomResponse(
            id=classroom_result.get('id'),
            name=request.name,
            code=code,
            teacher_id=current_user['id'],
            created_at=datetime.now(),
            student_count=0
        )
    except Exception as e:
        logger.error(f"❌ Create classroom error: {e}")
        raise HTTPException(status_code=500, detail="Failed to create classroom")

@router.get("/{classroom_id}/my-sessions")
async def get_my_classroom_sessions(
    classroom_id: str,
    current_user: dict = Depends(get_current_student)
):
    """Get all sessions for the current student in a specific classroom"""
    try:
        # In Supabase version, we'll just query the sessions table
        response = database.db.client.table("sessions").select("*").eq("classroom_id", classroom_id).eq("user_id", current_user['id']).execute()
        return response.data
    except Exception as e:
        logger.error(f"❌ Get my sessions error: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve sessions")

@router.post("/join", response_model=MessageResponse)
async def join_classroom(
    request: JoinClassroomRequest,
    current_user: dict = Depends(get_current_student)
):
    """Join a classroom using a code"""
    try:
        classroom = database.get_classroom_by_code(request.code)
        if not classroom:
            raise HTTPException(status_code=404, detail="Classroom code not found")
            
        database.add_student_to_classroom(classroom['id'], current_user['id'])
        return MessageResponse(message=f"Successfully joined classroom: {classroom['name']}", success=True)
    except HTTPException: raise
    except Exception as e:
        logger.error(f"❌ Join classroom error: {e}")
        raise HTTPException(status_code=500, detail="Failed to join classroom")

@router.get("/teacher/list", response_model=List[ClassroomResponse])
async def list_teacher_classrooms(current_user: dict = Depends(get_current_teacher)):
    """List classrooms created by teacher"""
    try:
        return database.get_teacher_classrooms(current_user['id'])
    except Exception as e:
        logger.error(f"❌ List teacher classrooms error: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve classrooms")

@router.get("/teacher/students")
async def get_all_my_students(current_user: dict = Depends(get_current_teacher)):
    """Get all students from all teacher classrooms"""
    try:
        response = database.db.client.table("classroom_students").select("student_id, profiles(*)").execute()
        return response.data
    except Exception as e:
        logger.error(f"❌ Get all teacher students error: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve students")

@router.get("/student/list", response_model=List[ClassroomResponse])
async def list_student_classrooms(current_user: dict = Depends(get_current_student)):
    """List classrooms student has joined"""
    try:
        response = database.db.client.table("classroom_students").select("classrooms(*)").eq("student_id", current_user['id']).execute()
        return [item['classrooms'] for item in response.data if item.get('classrooms')]
    except Exception as e:
        logger.error(f"❌ List student classrooms error: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve classrooms")
