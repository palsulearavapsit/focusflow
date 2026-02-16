"""
Machine Learning API Routes

This module provides API endpoints for the computer vision pipeline.

Available Endpoints:
- POST /api/ml/detect-face: Face detection only
- POST /api/ml/detect-emotion: Emotion detection (includes face detection)
- POST /api/ml/analyze-frame: Complete analysis (all three models)
- POST /api/ml/focus-metrics: Extract focus and attention metrics
- GET /api/ml/status: Get pipeline status

All endpoints require authentication.
"""

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from schemas import (
    FaceDetectionResult, 
    EmotionDetectionResult,
    CompleteAnalysisResult,
    FocusMetricsResult
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
    """
    Detect faces in uploaded frame
    
    Uses: detect_face.tflite model
    
    Returns:
    - face_detected: bool
    - face_count: int
    - confidence: float
    """
    try:
        contents = await file.read()
        result = ml_utils.detect_face(contents)
        
        # Extract first face details if detected
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
    """
    Detect emotion in uploaded frame
    
    Uses: 
    - detect_face.tflite (to locate face)
    - detect_emotion.h5 (to classify emotion)
    
    Returns:
    - emotion_detected: bool
    - emotion: str (e.g., "happy", "neutral")
    - confidence: float
    """
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
    """
    Complete frame analysis using all three models
    
    Pipeline:
    1. Face Detection (detect_face.tflite)
    2. Eye Tracking (track_eye.task)
    3. Emotion Detection (detect_emotion.h5)
    
    Returns comprehensive analysis with:
    - Face detection results
    - Eye tracking metrics (blink, gaze, attention)
    - Emotion classification
    - Processing time for each stage
    """
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
    """
    Extract focus and attention metrics from frame
    
    This endpoint runs the complete pipeline and extracts metrics
    relevant for study session tracking.
    
    Returns:
    - face_present: bool
    - multiple_faces: bool (distraction indicator)
    - eyes_open: bool
    - blink_detected: bool
    - attention_score: float (0-1)
    - gaze_centered: bool
    - emotion_state: str
    - engagement_score: float (0-1)
    - overall_focus_score: float (0-1)
    """
    try:
        contents = await file.read()
        metrics = ml_utils.get_focus_metrics(contents)
        
        return metrics
        
    except Exception as e:
        logger.error(f"Focus metrics API error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_ml_status():
    """
    Get ML pipeline status
    
    Returns status of all three models and pipeline readiness.
    No authentication required.
    """
    try:
        status = ml_utils.get_pipeline_status()
        return status
        
    except Exception as e:
        logger.error(f"Status API error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Legacy endpoint for backward compatibility
@router.post("/detect-eyes")
async def detect_eyes_endpoint(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_student)
):
    """
    Detect eyes in uploaded frame (deprecated)
    
    This endpoint is kept for backward compatibility.
    Use /analyze-frame or /focus-metrics instead for better results.
    """
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
            "confidence": 0.0
        }
