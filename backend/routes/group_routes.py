"""
FocusFlow Group Session Routes
Handles creating, joining and managing group study sessions (meetings)
"""

from fastapi import APIRouter, HTTPException, status, Depends
from typing import List
import string
import random
from schemas import (
    GroupSessionCreateRequest,
    GroupJoinRequest,
    GroupSessionResponse,
    GroupParticipantResponse,
    GroupMessageRequest,
    GroupMessageResponse,
    MessageResponse
)
from auth import get_current_user
from database import (
    create_group_session,
    get_group_session_by_code,
    add_participant_to_group,
    get_group_participants,
    end_group_session,
    send_group_message,
    get_group_messages_db
)
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/groups", tags=["Group Sessions"])

def generate_meeting_code() -> str:
    """Generate a unique 6-letter uppercase code"""
    return "".join(random.choices(string.ascii_uppercase, k=6))

@router.post("/create", response_model=GroupSessionResponse)
async def create_new_group(
    request: GroupSessionCreateRequest,
    current_user: dict = Depends(get_current_user)
):
    """Start a new group meeting session"""
    try:
        user_id = current_user["id"]
        
        # Keep trying until we find a unique code (though 6 letters is plenty)
        max_retries = 5
        meeting_code = ""
        for _ in range(max_retries):
            code = generate_meeting_code()
            if not get_group_session_by_code(code):
                meeting_code = code
                break
        
        if not meeting_code:
            raise HTTPException(status_code=500, detail="Could not generate unique meeting code")

        # 1. Create session in DB
        group_session = create_group_session(user_id, meeting_code)
        
        # 2. Host automatically joins too
        add_participant_to_group(group_session["id"], user_id)
        
        logger.info(f"✅ Group session created: {meeting_code} by user {user_id}")
        return group_session

    except Exception as e:
        logger.error(f"❌ Create group error: {e}")
        raise HTTPException(status_code=500, detail="Failed to create group session")


@router.post("/join", response_model=GroupSessionResponse)
async def join_group(
    request: GroupJoinRequest,
    current_user: dict = Depends(get_current_user)
):
    """Join an existing group meeting session using the 6-letter code"""
    try:
        user_id = current_user["id"]
        code = request.code.upper().strip()

        # 1. Check if meeting exists and is active
        group_session = get_group_session_by_code(code)
        if not group_session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invalid or expired meeting code"
            )

        # 2. Add user to participants list
        add_participant_to_group(group_session["id"], user_id)
        
        logger.info(f"👤 User {user_id} joined group {code}")
        return group_session

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Join group error: {e}")
        raise HTTPException(status_code=500, detail="Failed to join group")


@router.get("/{meeting_code}/participants", response_model=List[GroupParticipantResponse])
async def list_participants(
    meeting_code: str,
    current_user: dict = Depends(get_current_user)
):
    """Retrieve all current participants in a group session"""
    try:
        group_session = get_group_session_by_code(meeting_code)
        if not group_session:
            raise HTTPException(status_code=404, detail="Group session not found")

        participants = get_group_participants(group_session["id"])
        return participants

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Get participants error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get participant list")


@router.post("/{meeting_code}/end", response_model=MessageResponse)
async def close_group_session(
    meeting_code: str,
    current_user: dict = Depends(get_current_user)
):
    """Close the group session (only for host)"""
    try:
        user_id = current_user["id"]
        group_session = get_group_session_by_code(meeting_code)
        
        if not group_session:
            raise HTTPException(status_code=404, detail="Group session not found")
        
        if group_session["host_id"] != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the host can end the group session"
            )

        end_group_session(group_session["id"])
        logger.info(f"🛑 Group session {meeting_code} ended by host {user_id}")
        return MessageResponse(message="Group session ended successfully")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ End group session error: {e}")
        raise HTTPException(status_code=500, detail="Failed to end group session")


@router.get("/{meeting_code}/chat", response_model=List[GroupMessageResponse])
async def get_history(
    meeting_code: str,
    limit: int = 50,
    current_user: dict = Depends(get_current_user)
):
    """Retrieve chat history for the group session"""
    try:
        group_session = get_group_session_by_code(meeting_code)
        if not group_session:
            raise HTTPException(status_code=404, detail="Group session not found")

        messages = get_group_messages_db(group_session["id"], limit=limit)
        return messages

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Get chat history error: {e}")
        raise HTTPException(status_code=500, detail="Failed to load chat history")


@router.post("/{meeting_code}/chat", response_model=GroupMessageResponse)
async def send_message(
    meeting_code: str,
    request: GroupMessageRequest,
    current_user: dict = Depends(get_current_user)
):
    """Post a new message to the group session chat"""
    try:
        user_id = current_user["id"]
        group_session = get_group_session_by_code(meeting_code)
        
        if not group_session:
            raise HTTPException(status_code=404, detail="Group session not found")

        # Verify if user is actually in this group (optional security)
        participants = get_group_participants(group_session["id"])
        is_member = any(p["id"] == user_id for p in participants)
        if not is_member:
             raise HTTPException(status_code=403, detail="You are not a member of this group")

        message = send_group_message(
            group_session_id=group_session["id"],
            sender_id=user_id,
            content=request.content
        )
        return message

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Send group message error: {e}")
        raise HTTPException(status_code=500, detail="Failed to send group message")
