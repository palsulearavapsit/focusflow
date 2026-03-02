"""
FocusFlow Session Routes - MySQL Edition
Handles study session management endpoints
"""

from fastapi import APIRouter, HTTPException, status, Depends
from typing import List
from schemas import (
    SessionStartRequest,
    SessionEndRequest,
    SessionResponse,
    SessionSummaryResponse,
    MessageResponse
)
from auth import get_current_user
from database import (
    create_session, get_user_sessions,
    update_user_streak, update_user_title,
    update_session_focus_score
)
from ml_utils import calculate_advanced_focus_score, determine_user_title
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sessions", tags=["Sessions"])

# In-memory active session storage
active_sessions = {}


@router.post("/start", response_model=MessageResponse)
async def start_session(
    session_request: SessionStartRequest,
    current_user: dict = Depends(get_current_user)
):
    """Start a new study session"""
    try:
        user_id = current_user["id"]

        if user_id in active_sessions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You already have an active session. Please end it first."
            )

        active_sessions[user_id] = {
            "user_id": user_id,
            "technique": session_request.technique.value,
            "study_mode": session_request.study_mode.value,
            "camera_enabled": session_request.camera_enabled,
            "face_detection_enabled": session_request.camera_enabled,
            "emotion_detection_enabled": session_request.camera_enabled,
            "classroom_id": session_request.classroom_id,
            "start_time": datetime.now()
        }

        logger.info(f"✅ Session started for user {user_id}: {session_request.technique.value}")

        return MessageResponse(message="Study session started successfully", success=True)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Start session error: {e}")
        raise HTTPException(status_code=500, detail="Failed to start session. Please try again.")


@router.post("/end", response_model=SessionSummaryResponse)
async def end_session(
    session_data: SessionEndRequest,
    current_user: dict = Depends(get_current_user)
):
    """End current study session and save results"""
    try:
        user_id = current_user["id"]

        if user_id not in active_sessions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No active session found"
            )

        active_session = active_sessions[user_id]

        # Build complete session data for DB insert
        complete_session_data = {
            "user_id": user_id,
            "technique": active_session["technique"],
            "study_mode": active_session["study_mode"],
            "camera_enabled": active_session["camera_enabled"],
            "face_detection_enabled": active_session["face_detection_enabled"],
            "emotion_detection_enabled": active_session["emotion_detection_enabled"],
            "classroom_id": active_session.get("classroom_id"),
            "duration": session_data.duration,
            "distractions": session_data.distractions,
            "mouse_inactive_time": session_data.mouse_inactive_time,
            "keyboard_inactive_time": session_data.keyboard_inactive_time,
            "tab_switches": session_data.tab_switches,
            "camera_absence_time": session_data.camera_absence_time,
            "face_absence_time": session_data.face_absence_time,
            "dominant_emotion": session_data.dominant_emotion,
            "emotion_confidence": session_data.emotion_confidence,
            "user_state": session_data.user_state.value,
        }

        # Save session (MySQL trigger auto-calculates focus_score)
        saved_session = create_session(complete_session_data)
        session_id = saved_session["id"]

        # Override with advanced focus score if metrics provided
        advanced_result = None
        if (session_data.sustained_attention_minutes is not None and
                session_data.sustained_distraction_minutes is not None):

            duration_min = max(session_data.duration / 60.0, 0.1)

            advanced_result = calculate_advanced_focus_score(
                session_duration_minutes=duration_min,
                sustained_attention_minutes=session_data.sustained_attention_minutes,
                face_presence_minutes=(session_data.duration - session_data.camera_absence_time) / 60.0,
                sustained_distraction_minutes=session_data.sustained_distraction_minutes,
                distraction_events=session_data.distraction_events if session_data.distraction_events is not None else session_data.distractions,
                avg_recovery_time_seconds=session_data.avg_recovery_time_seconds or 0.0,
                emotion_stability_ratio=session_data.emotion_stability_ratio or 0.5
            )

            advanced_score = advanced_result["focus_score"]
            update_session_focus_score(session_id, advanced_score)
            saved_session["focus_score"] = advanced_score

            # Update streak and title
            if advanced_score >= 50:
                update_user_streak(user_id)

            new_title = determine_user_title(advanced_score, current_user["role"])
            if new_title:
                update_user_title(user_id, new_title)

        # Recalculate saved session from DB (to get trigger value if not overridden)
        latest = get_user_sessions(user_id, limit=1)
        if latest:
            saved_session = latest[0]

        del active_sessions[user_id]

        total_idle = session_data.mouse_inactive_time + session_data.keyboard_inactive_time
        idle_pct = (total_idle / session_data.duration * 100) if session_data.duration > 0 else 0

        logger.info(f"✅ Session ended for user {user_id}: Score {saved_session['focus_score']}")

        analysis_data = {
            "analysis": advanced_result.get("analysis") if advanced_result else None,
            "strength": advanced_result.get("strength") if advanced_result else None,
            "improvement_area": advanced_result.get("improvement_area") if advanced_result else None,
        }

        return SessionSummaryResponse(
            session_id=str(saved_session["id"]),
            technique=saved_session["technique"],
            study_mode=saved_session["study_mode"],
            duration_minutes=session_data.duration // 60,
            focus_score=float(saved_session["focus_score"]),
            distractions=session_data.distractions,
            user_state=session_data.user_state.value,
            camera_enabled=active_session["camera_enabled"],
            face_detection_enabled=active_session["face_detection_enabled"],
            emotion_detection_enabled=active_session["emotion_detection_enabled"],
            dominant_emotion=session_data.dominant_emotion,
            recommended_technique=saved_session.get("recommended_technique"),
            timestamp=saved_session["timestamp"],
            idle_time_percentage=round(idle_pct, 2),
            tab_switches=session_data.tab_switches,
            camera_absence_minutes=session_data.camera_absence_time // 60,
            face_absence_minutes=session_data.face_absence_time // 60,
            **analysis_data
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ End session error: {e}")
        raise HTTPException(status_code=500, detail="Failed to end session. Please try again.")


@router.get("/history", response_model=List[SessionResponse])
async def get_session_history(
    limit: int = 10,
    current_user: dict = Depends(get_current_user)
):
    """Get user's session history"""
    try:
        user_id = current_user["id"]
        sessions = get_user_sessions(user_id, limit=limit)

        result = []
        for s in sessions:
            s["id"] = str(s["id"])
            s["user_id"] = str(s["user_id"])
            result.append(SessionResponse(**s))

        logger.info(f"✅ Retrieved {len(result)} sessions for user {user_id}")
        return result

    except Exception as e:
        logger.error(f"❌ Get history error: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve session history")


@router.get("/active")
async def check_active_session(current_user: dict = Depends(get_current_user)):
    """Check if user has an active session"""
    user_id = current_user["id"]

    if user_id in active_sessions:
        session = active_sessions[user_id]
        elapsed = (datetime.now() - session["start_time"]).total_seconds()
        return {
            "success": True,
            "message": "Active session found",
            "session": {
                "technique": session["technique"],
                "study_mode": session["study_mode"],
                "start_time": session["start_time"].isoformat(),
                "elapsed_seconds": int(elapsed),
                "camera_enabled": session["camera_enabled"]
            }
        }

    return {"success": False, "message": "No active session"}


@router.delete("/cancel", response_model=MessageResponse)
async def cancel_session(current_user: dict = Depends(get_current_user)):
    """Cancel active session without saving"""
    try:
        user_id = current_user["id"]

        if user_id not in active_sessions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No active session to cancel"
            )

        del active_sessions[user_id]
        logger.info(f"✅ Session cancelled for user {user_id}")
        return MessageResponse(message="Session cancelled successfully", success=True)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Cancel session error: {e}")
        raise HTTPException(status_code=500, detail="Failed to cancel session")
