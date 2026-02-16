"""
Machine Learning Utilities

This module provides a simplified interface to the computer vision pipeline.
It wraps the modular three-stage pipeline for easy integration with existing code.

Pipeline Architecture:
┌─────────────────────────────────────────────────────────────────┐
│                    VIDEO FRAME INPUT                             │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  STAGE 1: Face Detection (detect_face.tflite)                   │
│  - Detect and localize faces                                    │
│  - Output: Bounding boxes, confidence scores                    │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
         ┌───────────────┴───────────────┐
         │                               │
         ▼                               ▼
┌──────────────────────┐    ┌──────────────────────────┐
│ STAGE 2: Eye Tracking│    │ STAGE 3: Emotion         │
│ (track_eye.task)     │    │ Detection                │
│                      │    │ (detect_emotion.h5)      │
│ - Eye landmarks      │    │ - Emotion classification │
│ - Blink detection    │    │ - Engagement metrics     │
│ - Gaze tracking      │    │ - Focus state            │
│ - Attention score    │    │                          │
└──────────────────────┘    └──────────────────────────┘
         │                               │
         └───────────────┬───────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│              COMBINED ANALYSIS OUTPUT                            │
│  - Face location                                                 │
│  - Eye metrics (blink, gaze, attention)                         │
│  - Emotion label and confidence                                 │
│  - Overall focus score                                          │
└─────────────────────────────────────────────────────────────────┘

Model Details:
1. detect_face.tflite: Lightweight TFLite model for face detection
2. track_eye.task: MediaPipe task for facial landmarks and eye tracking
3. detect_emotion.h5: Keras CNN for emotion classification

All models are pretrained and optimized for CPU inference.
"""

import logging
from typing import Dict, Tuple, Optional
from services.vision_pipeline import vision_pipeline

logger = logging.getLogger(__name__)


def load_models():
    """
    Load all ML models in the pipeline
    
    Models are automatically loaded when the vision_pipeline is initialized.
    This function is kept for backward compatibility.
    """
    status = vision_pipeline.get_pipeline_status()
    
    if status['pipeline_ready']:
        logger.info("✅ All models loaded successfully")
    else:
        logger.warning("⚠️ Some models failed to load. Check pipeline status:")
        for component, details in status['components'].items():
            if not details['model_loaded']:
                logger.error(f"   ❌ {component}: Not loaded - {details.get('model_path', 'Unknown path')}")
    
    return status['pipeline_ready']


def detect_face(image_bytes: bytes) -> Dict:
    """
    Detect faces in image with detailed metrics
    
    Returns:
        Dictionary with face_detected, face_count, bounding_boxes, confidence_scores
    """
    try:
        # Use face detector directly for detailed results
        result = vision_pipeline.face_detector.detect_faces(image_bytes)
        
        face_detected = result.get('face_detected', False)
        face_count = result.get('face_count', 0)
        
        logger.info(f"📸 Face detection: {face_count} face(s) detected")
        return result
        
    except Exception as e:
        logger.error(f"Error in detect_face: {e}")
        return {
            "face_detected": False, 
            "face_count": 0,
            "bounding_boxes": [],
            "confidence_scores": []
        }
        


def detect_emotion(image_bytes: bytes) -> Tuple[str, float]:
    """
    Detect emotion in image (backward compatible interface)
    
    This function maintains compatibility with existing code that expects
    an (emotion, confidence) tuple response.
    
    Args:
        image_bytes: Raw image bytes
        
    Returns:
        (emotion: str, confidence: float)
    """
    try:
        # Use simplified processing
        result = vision_pipeline.process_frame_simple(image_bytes)
        
        emotion = result.get('emotion', 'unknown')
        confidence = result.get('confidence', 0.0)
        
        logger.info(f"😊 Emotion detected: {emotion} ({confidence:.2f})")
        return emotion, confidence
        
    except Exception as e:
        logger.error(f"Error in detect_emotion: {e}")
        return "unknown", 0.0


def analyze_frame_complete(image_bytes: bytes) -> Dict:
    """
    Complete frame analysis using all three models
    
    This is the recommended function for new code.
    It provides full access to all pipeline capabilities.
    
    Args:
        image_bytes: Raw image bytes from camera/upload
        
    Returns:
        Dictionary containing:
        - success: bool
        - face_detected: bool
        - face_count: int
        - faces: List[Dict] with detailed analysis per face
        - processing_time_ms: float
        - pipeline_stages: Dict with timing for each stage
        
        Each face in 'faces' contains:
        - bounding_box: [x, y, w, h]
        - face_confidence: float
        - eye_tracking: Dict with eye metrics
        - emotion: Dict with emotion classification
    """
    try:
        result = vision_pipeline.process_frame(
            image_bytes,
            include_eye_tracking=True,
            include_emotion=True
        )
        
        logger.info(f"⚡ Complete analysis in {result.get('processing_time_ms', 0):.1f}ms")
        return result
        
    except Exception as e:
        logger.error(f"Error in complete frame analysis: {e}")
        return {
            "success": False,
            "face_detected": False,
            "face_count": 0,
            "faces": [],
            "error": str(e)
        }


def get_focus_metrics(image_bytes: bytes) -> Dict:
    """
    Get focus and attention metrics from frame
    
    This function runs the complete pipeline and extracts focus-relevant metrics.
    Useful for study session tracking and attention monitoring.
    
    Args:
        image_bytes: Raw image bytes
        
    Returns:
        Dictionary containing:
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
        # Run complete pipeline
        pipeline_result = vision_pipeline.process_frame(image_bytes)
        
        # Extract focus metrics
        focus_metrics = vision_pipeline.analyze_focus_metrics(pipeline_result)
        
        logger.info(f"🎯 Focus score: {focus_metrics.get('overall_focus_score', 0):.2f}")
        return focus_metrics
        
    except Exception as e:
        logger.error(f"Error getting focus metrics: {e}")
        return {
            "face_present": False,
            "overall_focus_score": 0.0,
            "error": str(e)
        }


def get_pipeline_status() -> Dict:
    """
    Get status of all models in the pipeline
    
    Returns:
        Dictionary with pipeline status and model details
    """
    return vision_pipeline.get_pipeline_status()


# Legacy compatibility functions
def detect_eyes(image_bytes: bytes) -> Tuple[bool, int]:
    """
    Legacy eye detection function (deprecated)
    
    Use analyze_frame_complete() or get_focus_metrics() instead.
    This function is kept for backward compatibility only.
    
    Returns:
        (eyes_detected: bool, eye_count: int)
    """
    logger.warning("detect_eyes() is deprecated. Use get_focus_metrics() instead.")
    
    try:
        result = vision_pipeline.process_frame(image_bytes, include_emotion=False)
        
        if not result['success'] or not result['face_detected']:
            return False, 0
        
        face = result['faces'][0]
        eye_data = face.get('eye_tracking', {})
        
        eyes_detected = eye_data.get('eyes_detected', False)
        # Estimate eye count (2 if detected, 0 if not)
        eye_count = 2 if eyes_detected else 0
        
        return eyes_detected, eye_count
        
    except Exception as e:
        logger.error(f"Error in detect_eyes: {e}")
        return False, 0


def load_model():
    """
    Legacy model loading function
    
    Kept for backward compatibility. Calls load_models().
    """
    return load_models()


def load_eye_model():
    """
    Legacy eye model loading function
    
    Kept for backward compatibility. Eye model is loaded automatically.
    """
    status = vision_pipeline.eye_tracker.get_status()
    return status['model_loaded']


# Module initialization
logger.info("📦 ML Utils initialized with modular vision pipeline")
logger.info("   Models: Face Detection (TFLite) + Eye Tracking (MediaPipe) + Emotion Detection (Keras)")
