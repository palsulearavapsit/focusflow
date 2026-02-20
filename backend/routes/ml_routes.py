from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from schemas import (
    FaceDetectionResult, 
    EmotionDetectionResult,
    CompleteAnalysisResult,
    FocusMetricsResult,
    DistractionAlertRequest,
    DistractionAlertResponse,
    FullscreenViolationRequest,
    FullscreenViolationResponse,
    StudyRoomModerationRequest,
    StudyRoomModerationResponse,
    CognitiveAnalysisRequest,
    CognitiveAnalysisResponse
)
from auth import get_current_student
import ml_utils
import logging

router = APIRouter(prefix="/api/ml", tags=["Machine Learning"])
logger = logging.getLogger(__name__)


@router.post("/detect-face", response_model=FaceDetectionResult)
async def detect_face_endpoint(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_student)
):
    try:
        contents = await file.read()
        result = ml_utils.detect_face(contents)
        
        bbox = None
        confidence = 0.0
        
        if result.get("face_detected") and result.get("bounding_boxes"):
            bbox = result["bounding_boxes"][0]
            confidence = result.get("confidence_scores", [0.0])[0]
        
        return FaceDetectionResult(
            face_detected=result.get("face_detected", False),
            face_count=result.get("face_count", 0),
            confidence=confidence,
            bounding_box=bbox
        )
        
    except Exception as e:
        logger.error(f"Face detection API error: {e}")
        return FaceDetectionResult(
            face_detected=False, 
            face_count=0, 
            confidence=0.0
        )


@router.post("/detect-emotion", response_model=EmotionDetectionResult)
async def detect_emotion_endpoint(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_student)
):
    try:
        contents = await file.read()
        emotion, confidence = ml_utils.detect_emotion(contents)
        
        return EmotionDetectionResult(
            emotion_detected=emotion != "unknown",
            emotion=emotion,
            confidence=confidence
        )
        
    except Exception as e:
        logger.error(f"Emotion detection API error: {e}")
        return EmotionDetectionResult(
            emotion_detected=False,
            emotion="unknown",
            confidence=0.0
        )


@router.post("/analyze-frame")
async def analyze_frame_endpoint(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_student)
):
    try:
        contents = await file.read()
        result = ml_utils.analyze_frame_complete(contents)
        
        return result
        
    except Exception as e:
        logger.error(f"Frame analysis API error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/focus-metrics")
async def focus_metrics_endpoint(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_student)
):
    try:
        contents = await file.read()
        metrics = ml_utils.get_focus_metrics(contents)
        
        return metrics
        
    except Exception as e:
        logger.error(f"Focus metrics API error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_ml_status():
    try:
        status = ml_utils.get_pipeline_status()
        return status
        
    except Exception as e:
        logger.error(f"Status API error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/detect-eyes")
async def detect_eyes_endpoint(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_student)
):
    logger.warning("detect-eyes endpoint is deprecated. Use /focus-metrics instead.")
    
    try:
        contents = await file.read()
        detected, count = ml_utils.detect_eyes(contents)
        
        return {
            "eyes_detected": detected,
            "eye_count": count,
            "confidence": 1.0 if detected else 0.0,
            "deprecated": True,
            "message": "Use /focus-metrics endpoint for comprehensive eye analysis"
        }
        
    except Exception as e:
        logger.error(f"Eye detection API error: {e}")
        return {
            "eyes_detected": False,
            "eye_count": 0,
            "confidence": 0.0,
            "deprecated": True,
            "message": "Use /focus-metrics endpoint for comprehensive eye analysis"
        }


@router.post("/evaluate-alert", response_model=DistractionAlertResponse)
async def evaluate_alert_endpoint(
    request: DistractionAlertRequest,
    current_user: dict = Depends(get_current_student)
):
    try:
        result = ml_utils.evaluate_distraction_alert(
            session_duration_minutes=request.session_duration_minutes,
            gaze_away_duration_30s=request.gaze_away_duration_30s,
            face_absence_duration_30s=request.face_absence_duration_30s,
            head_turned_duration=request.head_turned_duration,
            distraction_events_last_5_min=request.distraction_events_last_5_min,
            avg_recovery_time_seconds=request.avg_recovery_time_seconds,
            current_focus_score=request.current_focus_score
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Alert evaluation error: {e}")
        return {
            "alert_type": "NO_ALERT",
            "reason": "Error evaluating metrics",
            "message_to_user": ""
        }


@router.post("/fullscreen-violation", response_model=FullscreenViolationResponse)
async def evaluate_fullscreen_violation_endpoint(
    request: FullscreenViolationRequest,
    current_user: dict = Depends(get_current_student)
):
    try:
        violation_count = max(1, request.violation_count)
        
        result = ml_utils.evaluate_fullscreen_violation(
            session_duration_minutes=request.session_duration_minutes,
            violation_count=violation_count,
            last_violation_type=request.last_violation_type.value,
            time_since_last_violation_seconds=request.time_since_last_violation_seconds,
            current_focus_score=request.current_focus_score
        )
        
        return FullscreenViolationResponse(
            action=result['action'],
            penalty_percentage=result['penalty_percentage'],
            reason=result['reason'],
            message_to_user=result['message_to_user']
        )
        
    except Exception as e:
        logger.error(f"Fullscreen violation evaluation error: {e}")
        return FullscreenViolationResponse(
            action="SOFT_WARNING",
            penalty_percentage=0.0,
            reason="Error evaluating policy",
            message_to_user="Please stay in fullscreen mode."
        )


@router.post("/study-room-moderator", response_model=StudyRoomModerationResponse)
async def evaluate_study_room_moderator_endpoint(
    request: StudyRoomModerationRequest,
    current_user: dict = Depends(get_current_student)
):
    try:
        result = ml_utils.evaluate_study_room_policy(
            total_participants=request.total_participants,
            current_participant_focus_score=request.current_participant_focus_score,
            average_room_focus_score=request.average_room_focus_score,
            mic_status=request.mic_status,
            camera_status=request.camera_status,
            fullscreen_status=request.fullscreen_status,
            distraction_events_last_5_min=request.distraction_events_last_5_min,
            lock_mode_violations=request.lock_mode_violations,
            session_time_remaining_minutes=request.session_time_remaining_minutes
        )
        
        return StudyRoomModerationResponse(
            action=result['action'],
            penalty_percentage=result['penalty_percentage'],
            private_message=result['private_message'],
            room_message=result['room_message'],
            reason=result['reason']
        )
        
    except Exception as e:
        logger.error(f"Study room moderator error: {e}")
        return StudyRoomModerationResponse(
            action="NO_ACTION",
            penalty_percentage=0.0,
            private_message=None,
            room_message=None,
            reason="Error evaluating moderator policy"
        )


@router.post("/cognitive-refresh", response_model=CognitiveAnalysisResponse)
async def analyze_cognitive_refresh_endpoint(
    request: CognitiveAnalysisRequest,
    current_user: dict = Depends(get_current_student)
):
    try:
        import cognitive_engine
        result = cognitive_engine.analyze_cognitive_performance(
            game_type=request.game_type,
            current_metrics=request.current_metrics,
            previous_metrics=request.previous_metrics,
            focus_score=request.focus_score
        )
        
        return CognitiveAnalysisResponse(
            cognitive_refresh_score=result['cognitive_refresh_score'],
            cognitive_state=result['cognitive_state'],
            recommended_action=result['recommended_action'],
            analysis=result['analysis'],
            motivation_message=result['motivation_message']
        )
        
    except Exception as e:
        logger.error(f"Cognitive engine error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
