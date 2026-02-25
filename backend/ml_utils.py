import logging
import time
from typing import Dict, Tuple, Optional
from services.vision_pipeline import vision_pipeline

logger = logging.getLogger(__name__)


def load_models():
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
    with open("face_hits.log", "a") as logf:
        logf.write(f"Hit at {time.time()}\n")
    try:
        result = vision_pipeline.face_detector.detect_faces(image_bytes)
        
        face_detected = result.get('face_detected', False)
        face_count = result.get('face_count', 0)
        conf_scores = result.get('confidence_scores', [])
        max_conf = max(conf_scores) if conf_scores else 0.0
        
        logger.info(f"📸 Face detection: {face_count} face(s) detected (Max conf: {max_conf:.2f})")
        
        # DEBUG: Save failed frames for inspection
        if not face_detected:
            with open("debug_face_fail.jpg", "wb") as f:
                f.write(image_bytes)
        else:
            with open("debug_face_success.jpg", "wb") as f:
                f.write(image_bytes)
                
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
    try:
        result = vision_pipeline.process_frame_simple(image_bytes)
        
        emotion = result.get('emotion', 'unknown')
        confidence = result.get('confidence', 0.0)
        
        logger.info(f"😊 Emotion detected: {emotion} ({confidence:.2f})")
        return emotion, confidence
        
    except Exception as e:
        logger.error(f"Error in detect_emotion: {e}")
        return "unknown", 0.0


def analyze_frame_complete(image_bytes: bytes) -> Dict:
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
    try:
        pipeline_result = vision_pipeline.process_frame(image_bytes)
        
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
    return vision_pipeline.get_pipeline_status()


def detect_eyes(image_bytes: bytes) -> Tuple[bool, int]:
    logger.warning("detect_eyes() is deprecated. Use get_focus_metrics() instead.")
    
    try:
        result = vision_pipeline.process_frame(image_bytes, include_emotion=False)
        
        if not result['success'] or not result['face_detected']:
            return False, 0
        
        face = result['faces'][0]
        eye_data = face.get('eye_tracking', {})
        
        eyes_detected = eye_data.get('eyes_detected', False)
        eye_count = 2 if eyes_detected else 0
        
        return eyes_detected, eye_count
        
    except Exception as e:
        logger.error(f"Error in detect_eyes: {e}")
        return False, 0


def load_model():
    return load_models()


def load_eye_model():
    status = vision_pipeline.eye_tracker.get_status()
    return status['model_loaded']


logger.info("📦 ML Utils initialized with modular vision pipeline")
logger.info("   Models: Face Detection (TFLite) + Eye Tracking (MediaPipe) + Emotion Detection (Keras)")


def calculate_advanced_focus_score(
    session_duration_minutes: float,
    sustained_attention_minutes: float,
    face_presence_minutes: float,
    sustained_distraction_minutes: float,
    distraction_events: int,
    avg_recovery_time_seconds: float,
    emotion_stability_ratio: float
) -> Dict:
    import math

    # Normalize Inputs
    if session_duration_minutes <= 0.1:
        return {
            "focus_score": 0,
            "performance_level": "LOW",
            "analysis": "Session duration too short for analysis.",
            "strength": "N/A",
            "improvement_area": "N/A"
        }

    # --- 1. Virtual Start (Smoothing) ---
    # We add 5 "virtual minutes" of perfect focus to smooth out the start of sessions.
    # This prevents the score from dropping 50% because of one 30s mistake early on.
    SMOOTHING_FACTOR = 5.0 
    smoothed_duration = session_duration_minutes + SMOOTHING_FACTOR
    
    # --- 2. Sustained Attention Ratio (Smoothed) ---
    # Base: How much time spent in the focused window vs total
    attention_ratio = (sustained_attention_minutes + SMOOTHING_FACTOR) / smoothed_duration
    attention_ratio = max(0.0, min(1.0, attention_ratio))
    
    # --- 3. Presence Stability Ratio (Smoothed) ---
    # Base: How much time face was detected vs total
    presence_stability = (face_presence_minutes + SMOOTHING_FACTOR) / smoothed_duration
    presence_stability = max(0.0, min(1.0, presence_stability))
    
    # --- 4. Logarithmic Distraction Penalty ---
    # Instead of linear penalty, use log to make the first few mistakes "cheaper".
    # log2(distractions + 1) scales slowly. 
    # 0 dist = 0, 1 dist = 1, 3 dist = 2, 7 dist = 3, etc.
    distraction_penalty_factor = math.log2(max(1, distraction_events + 1)) - 1 # starts at -1 and goes up
    distraction_penalty_factor = max(0, distraction_penalty_factor) # ignore first distraction roughly
    
    # --- 5. Recovery Efficiency Ratio ---
    if distraction_events == 0:
        recovery_score = 1.0
    else:
        # Reward fast recovery (<10s), penalize slow (>60s)
        if avg_recovery_time_seconds <= 10:
            recovery_score = 1.0
        elif avg_recovery_time_seconds >= 60:
            recovery_score = 0.0
        else:
            # Linear decay from 10s to 60s
            recovery_score = 1.0 - ((avg_recovery_time_seconds - 10) / 50.0)
    recovery_score = max(0.0, min(1.0, recovery_score))

    # --- 6. Engagement Stability (Emotion) ---
    engagement_stability = max(0.0, min(1.0, emotion_stability_ratio))
    
    # --- 7. Final Scoring Formula (Weighted) ---
    raw_score = (
        (0.50 * attention_ratio) +
        (0.30 * presence_stability) +
        (0.15 * recovery_score) +
        (0.05 * engagement_stability)
    )

    # --- 8. Positive Reinforcement (Bonuses) ---
    bonus = 1.0
    # Bonus for zero distractions
    if distraction_events == 0:
        bonus += 0.05 
    # Bonus for long sessions (Deep Work reward)
    if session_duration_minutes >= 50:
        bonus += 0.03
        
    final_score = int(round(raw_score * 100 * bonus))
    
    # Hard bounds: 0 to 100
    final_score = max(0, min(100, final_score))
    
    # Determine Performance Level & Analysis
    if final_score >= 90:
        level = "EXCELLENT"
        analysis = "Exceptional focus performance. Your momentum was highly stable throughout the session."
    elif final_score >= 75:
        level = "HIGH"
        analysis = "Strong study session. You maintained consistency well and recovered quickly from minor interruptions."
    elif final_score >= 50:
        level = "MODERATE"
        analysis = "Average focus stability. You had periods of good work, but overall momentum was inconsistent."
    else:
        level = "LOW"
        analysis = "Focus needs improvement. Momentum was frequently broken. Consider shorter sessions with fewer environmental triggers."

    # Identify Strength
    metrics = {
        "Sustained Attention": attention_ratio,
        "Presence Consistency": presence_stability,
        "Distraction Recovery": recovery_score,
        "Emotional Stability": engagement_stability
    }
    strength_key = max(metrics, key=metrics.get)
    strength = f"Your {strength_key} was your strongest asset this session ({int(metrics[strength_key]*100)}%)."

    # Identify Improvement Area
    weakness_key = min(metrics, key=metrics.get)
    loss = (1.0 - metrics[weakness_key])
    if loss < 0.1:
        improvement = "Maintain this high level of focus and momentum."
    else:
        improvement = f"Aim to stabilize your {weakness_key} to build better momentum."

    return {
        "focus_score": final_score,
        "performance_level": level,
        "analysis": analysis,
        "strength": strength,
        "improvement_area": improvement
    }


def evaluate_distraction_alert(
    session_duration_minutes: float,
    gaze_away_duration_30s: float,
    face_absence_duration_30s: float,
    head_turned_duration: float,
    distraction_events_last_5_min: int,
    avg_recovery_time_seconds: float,
    current_focus_score: float
) -> Dict:
    
    if distraction_events_last_5_min >= 3 and session_duration_minutes > 5:
        return {
            "alert_type": "SUGGEST_BREAK",
            "reason": "Frequent distraction events detected (>2 in 5 mins).",
            "message_to_user": "You seem a bit distracted. Maybe take a short 2-minute break to reset?"
        }
        
    is_sustained_gaze = gaze_away_duration_30s >= 6
    is_sustained_absence = face_absence_duration_30s >= 7
    is_sustained_head_turn = head_turned_duration > 5
    
    if is_sustained_gaze or is_sustained_absence or is_sustained_head_turn:
        
        if avg_recovery_time_seconds < 10 and avg_recovery_time_seconds > 0:
            alert_type = "SOFT_ALERT"
            message = "Focus drifted, but you're bouncing back quickly. Keep it up!"
        else:
            alert_type = "STRONG_ALERT"
            message = "We noticed a sustained distraction. Let's refocus on the task."
            
        reason_parts = []
        if is_sustained_gaze: reason_parts.append(f"Gaze away ({gaze_away_duration_30s:.1f}s)")
        if is_sustained_absence: reason_parts.append(f"Face absence ({face_absence_duration_30s:.1f}s)")
        if is_sustained_head_turn: reason_parts.append(f"Head turned ({head_turned_duration:.1f}s)")
        
        return {
            "alert_type": alert_type,
            "reason": "Sustained distraction: " + ", ".join(reason_parts),
            "message_to_user": message
        }

    if current_focus_score < 50 and session_duration_minutes > 1:
        return {
            "alert_type": "SOFT_ALERT",
            "reason": "Overall focus score dropped below 50%.",
            "message_to_user": "Your focus level is dropping. Take a deep breath and center yourself."
        }
        
    return {
        "alert_type": "NO_ALERT",
        "reason": "Metrics within normal range.",
        "message_to_user": ""
    }


def evaluate_fullscreen_violation(
    session_duration_minutes: float,
    violation_count: int,
    last_violation_type: str,
    time_since_last_violation_seconds: float,
    current_focus_score: float
) -> Dict:
    
    current_violation_number = violation_count
    
    action = "SOFT_WARNING"
    penalty = 0.0
    reason = "First violation detected."
    message = "Please stay in fullscreen mode to maintain your focus session."
    
    if current_violation_number <= 1:
        action = "SOFT_WARNING"
        reason = "First violation warning."
        message = "Just a friendly reminder: staying in fullscreen helps you focus better."
        
    elif current_violation_number == 2:
        action = "STRONG_WARNING"
        reason = "Second violation detected."
        message = "We noticed you left fullscreen again. Please stay focused, or your score may be affected."
        
    elif current_violation_number == 3:
        action = "APPLY_SCORE_PENALTY"
        penalty = 5.0
        reason = "Third violation: Applying score penalty."
        message = "Repeated distractions detected. A small penalty has been applied to your focus score."
        
    elif current_violation_number >= 4:
        action = "END_SESSION"
        penalty = 10.0
        reason = "Maximum violations exceeded (4+)."
        message = "Session ended due to repeated fullscreen violations. Take a break and try again later."

    return {
        "action": action,
        "penalty_percentage": penalty,
        "reason": reason,
        "message_to_user": message
    }

