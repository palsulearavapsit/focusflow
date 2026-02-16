"""
Eye Tracking Service - MediaPipe Task Model Integration

This service handles eye tracking using MediaPipe's facial landmark detection.
Model: track_eye.task

Responsibilities:
- Detect facial landmarks with emphasis on eyes and iris
- Track eye openness and blink detection
- Estimate gaze direction and attention
- Provide iris center coordinates

Input: Cropped face region from face detection model
Output: Eye landmarks, blink detection, gaze metrics
"""

import cv2
import numpy as np
import os
import logging
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Try to import MediaPipe
try:
    import mediapipe as mp
    from mediapipe.tasks import python
    from mediapipe.tasks.python import vision
    MEDIAPIPE_AVAILABLE = True
except ImportError:
    MEDIAPIPE_AVAILABLE = False
    logger.warning("⚠️ MediaPipe not installed. Eye tracking will be disabled.")


class EyeTracker:
    """
    Eye Tracking using MediaPipe Face Landmarks
    
    This is the second stage of the pipeline (runs on cropped face regions).
    Provides detailed eye analysis for attention and focus detection.
    """
    
    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize the eye tracker
        
        Args:
            model_path: Path to track_eye.task model
        """
        if model_path is None:
            model_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                "models", "eye_tracking", "track_eye.task"
            )
        
        self.model_path = model_path
        self.landmarker = None
        self.model_loaded = False
        
        # Eye landmark indices (MediaPipe Face Mesh)
        self.LEFT_EYE_INDICES = [33, 160, 158, 133, 153, 144]
        self.RIGHT_EYE_INDICES = [362, 385, 387, 263, 373, 380]
        self.LEFT_IRIS_INDICES = [468, 469, 470, 471, 472]
        self.RIGHT_IRIS_INDICES = [473, 474, 475, 476, 477]
        
        # Blink detection thresholds
        self.EYE_ASPECT_RATIO_THRESHOLD = 0.2
        
        # Load model on initialization
        if MEDIAPIPE_AVAILABLE:
            self._load_model()
        else:
            logger.error("❌ MediaPipe not available. Cannot load eye tracking model.")
    
    def _load_model(self):
        """Load the MediaPipe eye tracking model"""
        try:
            if not os.path.exists(self.model_path):
                logger.error(f"❌ Eye tracking model not found at {self.model_path}")
                return
            
            # Create FaceLandmarker options
            base_options = python.BaseOptions(model_asset_path=self.model_path)
            options = vision.FaceLandmarkerOptions(
                base_options=base_options,
                output_face_blendshapes=False,
                output_facial_transformation_matrixes=False,
                num_faces=1  # We're processing single cropped face
            )
            
            # Create landmarker
            self.landmarker = vision.FaceLandmarker.create_from_options(options)
            
            self.model_loaded = True
            logger.info(f"✅ Eye tracking model loaded from {self.model_path}")
            
        except Exception as e:
            logger.error(f"❌ Failed to load eye tracking model: {e}")
            self.model_loaded = False
    
    def track_eyes(self, face_image_bytes: bytes) -> Dict:
        """
        Track eyes in cropped face image
        
        This is the main entry point for eye tracking.
        
        Args:
            face_image_bytes: Cropped face region (from face detector)
            
        Returns:
            Dictionary containing:
            - eyes_detected: bool
            - left_eye: {landmarks, iris_center, is_open, openness_score}
            - right_eye: {landmarks, iris_center, is_open, openness_score}
            - blink_detected: bool
            - gaze_direction: {horizontal, vertical} (-1 to 1)
            - attention_score: float (0 to 1)
        """
        if not MEDIAPIPE_AVAILABLE:
            return self._get_empty_result("MediaPipe not available")
        
        if not self.model_loaded:
            logger.warning("Eye tracking model not loaded, attempting reload...")
            self._load_model()
            
            if not self.model_loaded:
                return self._get_empty_result("Model not loaded")
        
        try:
            # Decode image
            nparr = np.frombuffer(face_image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if img is None:
                return self._get_empty_result("Failed to decode image")
            
            # Convert BGR to RGB
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            
            # Create MediaPipe Image
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=img_rgb)
            
            # Detect landmarks
            detection_result = self.landmarker.detect(mp_image)
            
            # Check if face landmarks were detected
            if not detection_result.face_landmarks or len(detection_result.face_landmarks) == 0:
                return self._get_empty_result("No face landmarks detected")
            
            # Get first face landmarks (we process one face at a time)
            face_landmarks = detection_result.face_landmarks[0]
            
            # Extract eye information
            left_eye_data = self._analyze_eye(face_landmarks, self.LEFT_EYE_INDICES, self.LEFT_IRIS_INDICES, img.shape)
            right_eye_data = self._analyze_eye(face_landmarks, self.RIGHT_EYE_INDICES, self.RIGHT_IRIS_INDICES, img.shape)
            
            # Detect blink
            blink_detected = self._detect_blink(left_eye_data, right_eye_data)
            
            # Estimate gaze direction
            gaze_direction = self._estimate_gaze(left_eye_data, right_eye_data)
            
            # Calculate attention score
            attention_score = self._calculate_attention_score(
                left_eye_data, right_eye_data, gaze_direction
            )
            
            result = {
                "eyes_detected": True,
                "left_eye": left_eye_data,
                "right_eye": right_eye_data,
                "blink_detected": blink_detected,
                "gaze_direction": gaze_direction,
                "attention_score": attention_score
            }
            
            logger.info(f"👁️ Eye tracking: Attention={attention_score:.2f}, Blink={blink_detected}")
            return result
            
        except Exception as e:
            logger.error(f"Error in eye tracking: {e}")
            return self._get_empty_result(str(e))
    
    def _analyze_eye(
        self, 
        landmarks: List, 
        eye_indices: List[int],
        iris_indices: List[int],
        image_shape: Tuple[int, int, int]
    ) -> Dict:
        """
        Analyze single eye (left or right)
        
        Args:
            landmarks: All face landmarks
            eye_indices: Indices for this eye's landmarks
            iris_indices: Indices for iris landmarks
            image_shape: Image dimensions
            
        Returns:
            Eye analysis data
        """
        try:
            height, width = image_shape[:2]
            
            # Extract eye landmarks
            eye_points = []
            for idx in eye_indices:
                lm = landmarks[idx]
                x = int(lm.x * width)
                y = int(lm.y * height)
                eye_points.append([x, y])
            
            # Extract iris center
            iris_center = None
            if iris_indices and len(iris_indices) > 0:
                # Use first iris landmark as center
                lm = landmarks[iris_indices[0]]
                iris_center = [int(lm.x * width), int(lm.y * height)]
            
            # Calculate Eye Aspect Ratio (EAR) for blink detection
            ear = self._calculate_eye_aspect_ratio(eye_points)
            
            # Determine if eye is open
            is_open = ear > self.EYE_ASPECT_RATIO_THRESHOLD
            
            return {
                "landmarks": eye_points,
                "iris_center": iris_center,
                "is_open": is_open,
                "openness_score": float(ear)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing eye: {e}")
            return {
                "landmarks": [],
                "iris_center": None,
                "is_open": False,
                "openness_score": 0.0
            }
    
    def _calculate_eye_aspect_ratio(self, eye_points: List[List[int]]) -> float:
        """
        Calculate Eye Aspect Ratio (EAR) for blink detection
        
        EAR = (||p2-p6|| + ||p3-p5||) / (2 * ||p1-p4||)
        
        Args:
            eye_points: List of eye landmark coordinates
            
        Returns:
            Eye aspect ratio (higher = more open)
        """
        try:
            if len(eye_points) < 6:
                return 0.0
            
            # Calculate vertical distances
            vertical1 = np.linalg.norm(np.array(eye_points[1]) - np.array(eye_points[5]))
            vertical2 = np.linalg.norm(np.array(eye_points[2]) - np.array(eye_points[4]))
            
            # Calculate horizontal distance
            horizontal = np.linalg.norm(np.array(eye_points[0]) - np.array(eye_points[3]))
            
            # Calculate EAR
            if horizontal == 0:
                return 0.0
            
            ear = (vertical1 + vertical2) / (2.0 * horizontal)
            return ear
            
        except Exception as e:
            logger.error(f"Error calculating EAR: {e}")
            return 0.0
    
    def _detect_blink(self, left_eye: Dict, right_eye: Dict) -> bool:
        """
        Detect if user is blinking
        
        Args:
            left_eye: Left eye analysis data
            right_eye: Right eye analysis data
            
        Returns:
            True if blink detected
        """
        # Blink detected if both eyes are closed
        return not left_eye["is_open"] and not right_eye["is_open"]
    
    def _estimate_gaze(self, left_eye: Dict, right_eye: Dict) -> Dict:
        """
        Estimate gaze direction from iris position
        
        Args:
            left_eye: Left eye analysis data
            right_eye: Right eye analysis data
            
        Returns:
            Gaze direction {horizontal, vertical} in range [-1, 1]
        """
        try:
            # Use iris centers if available
            left_iris = left_eye.get("iris_center")
            right_iris = right_eye.get("iris_center")
            
            if left_iris is None or right_iris is None:
                return {"horizontal": 0.0, "vertical": 0.0}
            
            # Calculate average iris position relative to eye landmarks
            # This is a simplified gaze estimation
            left_landmarks = left_eye.get("landmarks", [])
            right_landmarks = right_eye.get("landmarks", [])
            
            if not left_landmarks or not right_landmarks:
                return {"horizontal": 0.0, "vertical": 0.0}
            
            # Calculate eye centers
            left_center = np.mean(left_landmarks, axis=0)
            right_center = np.mean(right_landmarks, axis=0)
            
            # Calculate iris offset from eye center
            left_offset = np.array(left_iris) - left_center
            right_offset = np.array(right_iris) - right_center
            
            # Average offsets
            avg_offset = (left_offset + right_offset) / 2
            
            # Normalize to [-1, 1] range (rough approximation)
            horizontal = np.clip(avg_offset[0] / 10.0, -1.0, 1.0)
            vertical = np.clip(avg_offset[1] / 10.0, -1.0, 1.0)
            
            return {
                "horizontal": float(horizontal),
                "vertical": float(vertical)
            }
            
        except Exception as e:
            logger.error(f"Error estimating gaze: {e}")
            return {"horizontal": 0.0, "vertical": 0.0}
    
    def _calculate_attention_score(
        self, 
        left_eye: Dict, 
        right_eye: Dict,
        gaze: Dict
    ) -> float:
        """
        Calculate attention score based on eye metrics
        
        Args:
            left_eye: Left eye data
            right_eye: Right eye data
            gaze: Gaze direction
            
        Returns:
            Attention score (0 to 1)
        """
        try:
            # Base score on eye openness
            left_openness = left_eye.get("openness_score", 0.0)
            right_openness = right_eye.get("openness_score", 0.0)
            avg_openness = (left_openness + right_openness) / 2
            
            # Penalize for extreme gaze angles (looking away)
            gaze_penalty = abs(gaze["horizontal"]) * 0.3 + abs(gaze["vertical"]) * 0.2
            
            # Calculate attention score
            attention = avg_openness - gaze_penalty
            attention = np.clip(attention, 0.0, 1.0)
            
            return float(attention)
            
        except Exception as e:
            logger.error(f"Error calculating attention score: {e}")
            return 0.0
    
    def _get_empty_result(self, message: str = "") -> Dict:
        """Return empty result when tracking fails"""
        return {
            "eyes_detected": False,
            "left_eye": {
                "landmarks": [],
                "iris_center": None,
                "is_open": False,
                "openness_score": 0.0
            },
            "right_eye": {
                "landmarks": [],
                "iris_center": None,
                "is_open": False,
                "openness_score": 0.0
            },
            "blink_detected": False,
            "gaze_direction": {"horizontal": 0.0, "vertical": 0.0},
            "attention_score": 0.0,
            "message": message
        }
    
    def get_status(self) -> Dict:
        """Get eye tracker status"""
        return {
            "model_loaded": self.model_loaded,
            "model_path": self.model_path,
            "mediapipe_available": MEDIAPIPE_AVAILABLE,
            "model_type": "MediaPipe Face Landmarker",
            "capabilities": [
                "Eye landmark detection",
                "Blink detection",
                "Iris tracking",
                "Gaze estimation",
                "Attention scoring"
            ]
        }


# Global instance
eye_tracker = EyeTracker()
