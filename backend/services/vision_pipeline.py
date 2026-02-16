"""
Computer Vision Pipeline Orchestrator

This module orchestrates the three-stage computer vision pipeline:
1. Face Detection (TFLite) - Detect and localize faces
2. Eye Tracking (MediaPipe Task) - Track eyes, blinks, and gaze
3. Emotion Detection (Keras H5) - Classify facial emotions

Pipeline Flow:
- Input: Video frame (bytes)
- Stage 1: Detect faces and get bounding boxes
- Stage 2: For each face, crop and run eye tracking
- Stage 3: For each face, crop and run emotion detection
- Output: Combined results with face location, eye metrics, and emotion

This modular design ensures:
- Clear separation of concerns
- Independent model responsibilities
- Easy maintenance and testing
- Scalable architecture
"""

import logging
from typing import Dict, List, Optional
import time

from services.face_detector import face_detector
from services.eye_tracker import eye_tracker
from services.emotion_detector import emotion_detector

logger = logging.getLogger(__name__)


class VisionPipeline:
    """
    Unified Computer Vision Pipeline
    
    Orchestrates the three pretrained models in a sequential pipeline.
    Each model outputs feed into the next, creating a comprehensive analysis.
    """
    
    def __init__(self):
        """Initialize the vision pipeline"""
        self.face_detector = face_detector
        self.eye_tracker = eye_tracker
        self.emotion_detector = emotion_detector
        
        logger.info("🚀 Vision Pipeline initialized")
        self._log_pipeline_status()
    
    def _log_pipeline_status(self):
        """Log the status of all pipeline components"""
        face_status = self.face_detector.get_status()
        eye_status = self.eye_tracker.get_status()
        emotion_status = self.emotion_detector.get_status()
        
        logger.info("📊 Pipeline Status:")
        logger.info(f"   Face Detection: {'✅ Ready' if face_status['model_loaded'] else '❌ Not Ready'}")
        logger.info(f"   Eye Tracking: {'✅ Ready' if eye_status['model_loaded'] else '❌ Not Ready'}")
        logger.info(f"   Emotion Detection: {'✅ Ready' if emotion_status['model_loaded'] else '❌ Not Ready'}")
    
    def process_frame(
        self, 
        frame_bytes: bytes,
        include_eye_tracking: bool = True,
        include_emotion: bool = True
    ) -> Dict:
        """
        Process a single video frame through the complete pipeline
        
        This is the main entry point for frame analysis.
        
        Args:
            frame_bytes: Raw frame image bytes
            include_eye_tracking: Whether to run eye tracking (default: True)
            include_emotion: Whether to run emotion detection (default: True)
            
        Returns:
            Dictionary containing:
            - success: bool
            - face_detected: bool
            - face_count: int
            - faces: List of face analysis results
            - processing_time_ms: float
            - pipeline_stages: Dict of stage execution times
        """
        start_time = time.time()
        stage_times = {}
        
        try:
            # ========================================
            # STAGE 1: FACE DETECTION
            # ========================================
            stage1_start = time.time()
            face_result = self.face_detector.detect_faces(frame_bytes)
            stage_times['face_detection_ms'] = (time.time() - stage1_start) * 1000
            
            if not face_result['face_detected']:
                return {
                    "success": True,
                    "face_detected": False,
                    "face_count": 0,
                    "faces": [],
                    "processing_time_ms": (time.time() - start_time) * 1000,
                    "pipeline_stages": stage_times
                }
            
            # Process each detected face
            faces_analysis = []
            
            for idx, (bbox, confidence) in enumerate(zip(
                face_result['bounding_boxes'],
                face_result['confidence_scores']
            )):
                face_data = {
                    "face_id": idx,
                    "bounding_box": bbox,
                    "face_confidence": confidence,
                    "eye_tracking": None,
                    "emotion": None
                }
                
                # ========================================
                # STAGE 2: EYE TRACKING (per face)
                # ========================================
                if include_eye_tracking:
                    stage2_start = time.time()
                    
                    # Crop face region for eye tracking
                    face_crop = self.face_detector.crop_face_region(frame_bytes, bbox)
                    
                    if face_crop:
                        eye_result = self.eye_tracker.track_eyes(face_crop)
                        face_data['eye_tracking'] = eye_result
                        
                        if idx == 0:  # Log only for first face
                            stage_times['eye_tracking_ms'] = (time.time() - stage2_start) * 1000
                
                # ========================================
                # STAGE 3: EMOTION DETECTION (per face)
                # ========================================
                if include_emotion:
                    stage3_start = time.time()
                    
                    # Crop face region for emotion detection
                    if not include_eye_tracking:  # Avoid re-cropping if already done
                        face_crop = self.face_detector.crop_face_region(frame_bytes, bbox)
                    
                    if face_crop:
                        emotion_result = self.emotion_detector.detect_emotion(face_crop)
                        face_data['emotion'] = emotion_result
                        
                        if idx == 0:  # Log only for first face
                            stage_times['emotion_detection_ms'] = (time.time() - stage3_start) * 1000
                
                faces_analysis.append(face_data)
            
            # Calculate total processing time
            total_time = (time.time() - start_time) * 1000
            
            result = {
                "success": True,
                "face_detected": True,
                "face_count": len(faces_analysis),
                "faces": faces_analysis,
                "processing_time_ms": total_time,
                "pipeline_stages": stage_times
            }
            
            logger.info(f"⚡ Pipeline completed in {total_time:.1f}ms")
            return result
            
        except Exception as e:
            logger.error(f"Error in vision pipeline: {e}")
            return {
                "success": False,
                "face_detected": False,
                "face_count": 0,
                "faces": [],
                "error": str(e),
                "processing_time_ms": (time.time() - start_time) * 1000,
                "pipeline_stages": stage_times
            }
    
    def analyze_focus_metrics(self, pipeline_result: Dict) -> Dict:
        """
        Extract focus-relevant metrics from pipeline results
        
        This combines outputs from all three models to generate
        comprehensive focus and attention metrics.
        
        Args:
            pipeline_result: Output from process_frame()
            
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
            if not pipeline_result.get('success') or not pipeline_result.get('face_detected'):
                return self._get_empty_focus_metrics()
            
            faces = pipeline_result.get('faces', [])
            
            if len(faces) == 0:
                return self._get_empty_focus_metrics()
            
            # Use first face for analysis (primary user)
            primary_face = faces[0]
            
            # Extract eye tracking metrics
            eye_data = primary_face.get('eye_tracking', {})
            eyes_detected = eye_data.get('eyes_detected', False)
            attention_score = eye_data.get('attention_score', 0.0)
            blink_detected = eye_data.get('blink_detected', False)
            gaze = eye_data.get('gaze_direction', {})
            
            # Determine if gaze is centered (looking at screen)
            gaze_centered = (
                abs(gaze.get('horizontal', 0)) < 0.3 and
                abs(gaze.get('vertical', 0)) < 0.3
            )
            
            # Check if eyes are open
            left_eye = eye_data.get('left_eye', {})
            right_eye = eye_data.get('right_eye', {})
            eyes_open = left_eye.get('is_open', False) or right_eye.get('is_open', False)
            
            # Extract emotion metrics
            emotion_data = primary_face.get('emotion', {})
            emotion_detected = emotion_data.get('emotion_detected', False)
            emotion_state = emotion_data.get('dominant_emotion', 'unknown')
            
            # Calculate engagement from emotion
            if emotion_detected:
                all_emotions = emotion_data.get('all_emotions', {})
                engagement_score = self.emotion_detector.calculate_engagement_score(all_emotions)
            else:
                engagement_score = 0.0
            
            # Calculate overall focus score
            # Weights: face(0.2) + eyes(0.3) + gaze(0.2) + emotion(0.3)
            overall_focus = (
                0.2 * (1.0 if eyes_detected else 0.0) +
                0.3 * attention_score +
                0.2 * (1.0 if gaze_centered else 0.5) +
                0.3 * engagement_score
            )
            
            # Penalize for multiple faces (distraction)
            multiple_faces = len(faces) > 1
            if multiple_faces:
                overall_focus *= 0.7
            
            return {
                "face_present": True,
                "multiple_faces": multiple_faces,
                "eyes_open": eyes_open,
                "blink_detected": blink_detected,
                "attention_score": attention_score,
                "gaze_centered": gaze_centered,
                "emotion_state": emotion_state,
                "engagement_score": engagement_score,
                "overall_focus_score": overall_focus
            }
            
        except Exception as e:
            logger.error(f"Error analyzing focus metrics: {e}")
            return self._get_empty_focus_metrics()
    
    def _get_empty_focus_metrics(self) -> Dict:
        """Return empty focus metrics when no face detected"""
        return {
            "face_present": False,
            "multiple_faces": False,
            "eyes_open": False,
            "blink_detected": False,
            "attention_score": 0.0,
            "gaze_centered": False,
            "emotion_state": "unknown",
            "engagement_score": 0.0,
            "overall_focus_score": 0.0
        }
    
    def get_pipeline_status(self) -> Dict:
        """
        Get comprehensive pipeline status
        
        Returns:
            Status of all pipeline components
        """
        return {
            "pipeline_ready": all([
                self.face_detector.get_status()['model_loaded'],
                self.eye_tracker.get_status()['model_loaded'],
                self.emotion_detector.get_status()['model_loaded']
            ]),
            "components": {
                "face_detection": self.face_detector.get_status(),
                "eye_tracking": self.eye_tracker.get_status(),
                "emotion_detection": self.emotion_detector.get_status()
            },
            "pipeline_version": "1.0.0",
            "architecture": "Sequential 3-stage pipeline",
            "optimization": "Real-time CPU inference"
        }
    
    def process_frame_simple(self, frame_bytes: bytes) -> Dict:
        """
        Simplified frame processing for backward compatibility
        
        Returns basic face and emotion detection without detailed metrics.
        
        Args:
            frame_bytes: Raw frame bytes
            
        Returns:
            Simplified result dict for compatibility with existing code
        """
        result = self.process_frame(frame_bytes)
        
        if not result['success'] or not result['face_detected']:
            return {
                "face_detected": False,
                "face_count": 0,
                "emotion": "unknown",
                "confidence": 0.0
            }
        
        # Get first face data
        face = result['faces'][0]
        emotion_data = face.get('emotion', {})
        
        return {
            "face_detected": True,
            "face_count": result['face_count'],
            "emotion": emotion_data.get('dominant_emotion', 'unknown'),
            "confidence": emotion_data.get('confidence', 0.0)
        }


# Global pipeline instance
vision_pipeline = VisionPipeline()


# Convenience functions for easy access
def process_frame(frame_bytes: bytes, **kwargs) -> Dict:
    """Process a video frame through the pipeline"""
    return vision_pipeline.process_frame(frame_bytes, **kwargs)


def analyze_focus(pipeline_result: Dict) -> Dict:
    """Analyze focus metrics from pipeline result"""
    return vision_pipeline.analyze_focus_metrics(pipeline_result)


def get_status() -> Dict:
    """Get pipeline status"""
    return vision_pipeline.get_pipeline_status()
