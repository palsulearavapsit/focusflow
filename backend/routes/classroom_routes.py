"""
FocusFlow Classroom Routes - MySQL Edition
"""

from datetime import datetime
from fastapi import APIRouter, HTTPException, status, Depends
from typing import List
import string, random, logging

from schemas import (
    ClassroomCreateRequest,
    JoinClassroomRequest,
    ClassroomResponse,
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


def _to_classroom_response(row: dict) -> dict:
    """Convert DB row ids to strings for response"""
    row = dict(row)
    row["id"] = str(row["id"])
    row["teacher_id"] = str(row["teacher_id"])
    return row


@router.post("/create", response_model=ClassroomResponse)
async def create_new_classroom(
    request: ClassroomCreateRequest,
    current_user: dict = Depends(get_current_teacher)
):
    """Create a new classroom"""
    try:
        code = generate_classroom_code()
        classroom = database.create_classroom(request.name, code, current_user["id"])
        return _to_classroom_response(classroom)
    except Exception as e:
        logger.error(f"❌ Create classroom error: {e}")
        raise HTTPException(status_code=500, detail="Failed to create classroom")


@router.post("/join", response_model=MessageResponse)
async def join_classroom(
    request: JoinClassroomRequest,
    current_user: dict = Depends(get_current_student)
):
    """Join a classroom using code"""
    try:
        classroom = database.get_classroom_by_code(request.code)
        if not classroom:
            raise HTTPException(status_code=404, detail="Classroom code not found")
        database.add_student_to_classroom(classroom["id"], current_user["id"])
        return MessageResponse(message=f"Successfully joined classroom: {classroom['name']}", success=True)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Join classroom error: {e}")
        raise HTTPException(status_code=500, detail="Failed to join classroom")


@router.get("/teacher/list", response_model=List[ClassroomResponse])
async def list_teacher_classrooms(current_user: dict = Depends(get_current_teacher)):
    """List classrooms created by teacher"""
    try:
        classrooms = database.get_teacher_classrooms(current_user["id"])
        return [_to_classroom_response(c) for c in classrooms]
    except Exception as e:
        logger.error(f"❌ List teacher classrooms error: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve classrooms")


@router.get("/teacher/students")
async def get_all_my_students(current_user: dict = Depends(get_current_teacher)):
    """Get all students across teacher's classrooms"""
    try:
        students = database.get_teacher_students(current_user["id"])
        for s in students:
            s["id"] = str(s["id"])
        return students
    except Exception as e:
        logger.error(f"❌ Get all teacher students error: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve students")


@router.get("/student/list", response_model=List[ClassroomResponse])
async def list_student_classrooms(current_user: dict = Depends(get_current_student)):
    """List classrooms student has joined"""
    try:
        classrooms = database.get_student_classrooms(current_user["id"])
        return [_to_classroom_response(c) for c in classrooms]
    except Exception as e:
        logger.error(f"❌ List student classrooms error: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve classrooms")


@router.get("/{classroom_id}/my-sessions")
async def get_my_classroom_sessions(
    classroom_id: int,
    current_user: dict = Depends(get_current_student)
):
    """Get sessions for the current student in a specific classroom"""
    try:
        sessions = database.get_classroom_sessions(classroom_id, user_id=current_user["id"])
        for s in sessions:
            s["id"] = str(s["id"])
            s["user_id"] = str(s["user_id"])
        return sessions
    except Exception as e:
        logger.error(f"❌ Get my sessions error: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve sessions")


# ─── Routes used by classroom_stats.html ─────────────────────────────────────

@router.get("/{classroom_id}")
async def get_classroom_detail(
    classroom_id: int,
    current_user: dict = Depends(get_current_teacher)
):
    """Get full classroom detail + student stats"""
    try:
        data = database.get_classroom_detail(classroom_id)
        if not data:
            raise HTTPException(status_code=404, detail="Classroom not found")

        # Stringify IDs for frontend
        cls = dict(data["classroom"])
        cls["id"] = str(cls["id"])
        cls["teacher_id"] = str(cls["teacher_id"])

        students = []
        for s in data["students"]:
            row = dict(s)
            row["student_id"] = str(row["student_id"])
            row["avg_focus_score"] = float(row["avg_focus_score"])
            row["total_study_time"] = int(row["total_study_time"])
            row["total_sessions"] = int(row["total_sessions"])
            students.append(row)

        return {"classroom": cls, "students": students}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Get classroom detail error: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve classroom")


@router.get("/{classroom_id}/students/{student_id}/sessions")
async def get_student_sessions_in_classroom(
    classroom_id: int,
    student_id: int,
    current_user: dict = Depends(get_current_teacher)
):
    """Get all sessions of a specific student in a classroom"""
    try:
        sessions = database.get_student_classroom_sessions(classroom_id, student_id)
        for s in sessions:
            s["id"] = str(s["id"])
            s["user_id"] = str(s["user_id"])
        return sessions
    except Exception as e:
        logger.error(f"❌ Get student sessions error: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve sessions")


@router.put("/{classroom_id}/students/{student_id}/role")
async def update_student_role(
    classroom_id: int,
    student_id: int,
    request: UpdateRoleRequest,
    current_user: dict = Depends(get_current_teacher)
):
    """Update a student's role in a classroom"""
    try:
        database.update_student_role_in_classroom(classroom_id, student_id, request.role)
        return {"success": True, "message": "Role updated"}
    except Exception as e:
        logger.error(f"❌ Update role error: {e}")
        raise HTTPException(status_code=500, detail="Failed to update role")


@router.delete("/{classroom_id}/students/{student_id}")
async def remove_student(
    classroom_id: int,
    student_id: int,
    current_user: dict = Depends(get_current_teacher)
):
    """Remove a student from a classroom"""
    try:
        database.remove_student_from_classroom(classroom_id, student_id)
        return {"success": True, "message": "Student removed"}
    except Exception as e:
        logger.error(f"❌ Remove student error: {e}")
        raise HTTPException(status_code=500, detail="Failed to remove student")

@router.delete("/{classroom_id}", response_model=MessageResponse)
async def delete_classroom(
    classroom_id: int,
    current_user: dict = Depends(get_current_teacher)
):
    """Delete a classroom (teacher only deletes their own)"""
    try:
        # Verify ownership
        classrooms = database.get_teacher_classrooms(current_user["id"])
        if not any(c["id"] == classroom_id for c in classrooms):
            raise HTTPException(status_code=403, detail="Not authorized to delete this classroom")
            
        database.delete_classroom(classroom_id)
        return MessageResponse(message="Classroom deleted successfully", success=True)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Delete classroom error: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete classroom")
