"""
FocusFlow - Discussion Forum Chat Routes
Handles private 1-on-1 messaging between students and teachers.
Privacy: Only participants of a conversation can access it.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict
import logging
from auth import get_current_user
from database import (
    get_chat_contacts,
    get_chat_history,
    send_chat_message,
    get_unread_count,
    mark_messages_read
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/chat", tags=["Discussion Forum"])


class SendMessageRequest(BaseModel):
    receiver_id: int
    content: str


@router.get("/contacts")
async def get_contacts(current_user: Dict = Depends(get_current_user)):
    """
    Get list of people this user can chat with.
    - Students see: their classmates + their teachers
    - Teachers see: their students
    """
    try:
        contacts = get_chat_contacts(
            user_id=current_user["id"],
            role=current_user["role"]
        )
        return contacts
    except Exception as e:
        logger.error(f"Error fetching contacts: {e}")
        raise HTTPException(status_code=500, detail="Failed to load contacts")


@router.get("/history/{contact_id}")
async def get_history(contact_id: int, current_user: Dict = Depends(get_current_user)):
    """
    Get private chat history between the current user and contact_id.
    PRIVACY ENFORCED: The query strictly filters to only messages where
    (sender=me AND receiver=contact) OR (sender=contact AND receiver=me).
    No other user can access this data.
    """
    try:
        messages = get_chat_history(
            user_id=current_user["id"],
            contact_id=contact_id
        )
        return messages
    except Exception as e:
        logger.error(f"Error fetching chat history: {e}")
        raise HTTPException(status_code=500, detail="Failed to load messages")


@router.post("/send")
async def send_message(
    request: SendMessageRequest,
    current_user: Dict = Depends(get_current_user)
):
    """
    Send a private message to another user.
    Validates that the sender is not messaging themselves.
    """
    if request.receiver_id == current_user["id"]:
        raise HTTPException(status_code=400, detail="Cannot send message to yourself")

    if not request.content.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    try:
        message = send_chat_message(
            sender_id=current_user["id"],
            receiver_id=request.receiver_id,
            content=request.content.strip()
        )
        return message
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        raise HTTPException(status_code=500, detail="Failed to send message")


@router.get("/unread")
async def get_unread(current_user: Dict = Depends(get_current_user)):
    """Get total unread message count for badge display."""
    try:
        count = get_unread_count(current_user["id"])
        return {"unread_count": count}
    except Exception as e:
        logger.error(f"Error fetching unread count: {e}")
        return {"unread_count": 0}


@router.post("/read/{sender_id}")
async def mark_as_read(sender_id: int, current_user: Dict = Depends(get_current_user)):
    """Mark all messages from sender_id to current_user as read."""
    try:
        mark_messages_read(receiver_id=current_user["id"], sender_id=sender_id)
        return {"success": True}
    except Exception as e:
        logger.error(f"Error marking messages as read: {e}")
        raise HTTPException(status_code=500, detail="Failed to mark as read")
