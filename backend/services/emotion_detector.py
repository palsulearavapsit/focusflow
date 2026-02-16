"""
Emotion Detection Service - Keras H5 Model Integration

This service handles emotion detection using a pretrained CNN model.
Model: detect_emotion.h5

Responsibilities:
- Classify facial emotions from cropped face images
- Return emotion probabilities for multiple classes
- Identify dominant emotion

Input: Cropped face region from face detection model
Output: Emotion class, confidence, probability distribution

Emotion Classes:
- Angry, Disgust, Fear, Happy, Sad, Surprise, Neutral
"""

import cv2
import numpy as np
import os
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Try to import TensorFlow/Keras
try:
    import tensorflow as tf
    from tensorflow import keras
    TF_AVAILABLE = True
except ImportError:
    TF_AVAILABLE = False
    logger.warning("⚠️ TensorFlow not installed. Emotion detection will be disabled.")


class EmotionDetector:
    """
    Emotion Detection using pretrained Keras CNN model
    
    This is the third stage of the pipeline (runs on cropped face regions).
    Classifies emotions to detect engagement and focus levels.
    """
    
    # Standard emotion classes (FER2013 dataset format)
    EMOTION_CLASSES = [
        "angry",      # 0
        "disgust",    # 1
        "fear",       # 2
        "happy",      # 3
        "sad",        # 4
        "surprise",   # 5
        "neutral"     # 6
    ]
    
    # Mapping to focus-relevant categories
    FOCUS_MAPPING = {
        "angry": "distracted",
        "disgust": "distracted",
        "fear": "distracted",
        "happy": "engaged",
        "sad": "low_energy",
        "surprise": "alert",
        "neutral": "focused"
    }
    
    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize the emotion detector
        
        Args:
            model_path: Path to detect_emotion.h5 model
        """
        if model_path is None:
            model_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                "models", "emotion_detection", "detect_emotion.h5"
            )
        
        self.model_path = model_path
        self.model = None
        self.model_loaded = False
        self.input_shape = (48, 48)  # Standard FER2013 input size
        
        # Load model on initialization
        if TF_AVAILABLE:
            self._load_model()
        else:
            logger.error("❌ TensorFlow not available. Cannot load emotion detection model.")
    
    def _load_model(self):
        """Load the Keras emotion detection model"""
        try:
            if not os.path.exists(self.model_path):
                logger.error(f"❌ Emotion detection model not found at {self.model_path}")
                return
            
            # Load Keras H5 model
            self.model = keras.models.load_model(self.model_path, compile=False)
            
            # Get input shape from model
            input_shape = self.model.input_shape
            if len(input_shape) >= 3:
                self.input_shape = (input_shape[1], input_shape[2])
            
            self.model_loaded = True
            logger.info(f"✅ Emotion detection model loaded from {self.model_path}")
            logger.info(f"   Input shape: {self.model.input_shape}")
            logger.info(f"   Output shape: {self.model.output_shape}")
            logger.info(f"   Emotion classes: {self.EMOTION_CLASSES}")
            
        except Exception as e:
            logger.error(f"❌ Failed to load emotion detection model: {e}")
            self.model_loaded = False
    
    def preprocess_face(self, face_image_bytes: bytes) -> Optional[np.ndarray]:
        """
        Preprocess face image for emotion detection
        
        Args:
            face_image_bytes: Cropped face region bytes
            
        Returns:
            Preprocessed image array or None if error
        """
        try:
            # Decode image
            nparr = np.frombuffer(face_image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)  # Most emotion models use grayscale
            
            if img is None:
                logger.error("Failed to decode face image")
                return None
            
            # Resize to model input size
            img_resized = cv2.resize(img, self.input_shape)
            
            # Normalize pixel values
            img_normalized = img_resized.astype('float32') / 255.0
            
            # Add channel dimension if needed (grayscale)
            if len(self.model.input_shape) == 4:
                img_normalized = np.expand_dims(img_normalized, axis=-1)
            
            # Add batch dimension
            img_batch = np.expand_dims(img_normalized, axis=0)
            
            return img_batch
            
        except Exception as e:
            logger.error(f"Error preprocessing face image: {e}")
            return None
    
    def detect_emotion(self, face_image_bytes: bytes) -> Dict:
        """
        Detect emotion from cropped face image
        
        This is the main entry point for emotion detection.
        
        Args:
            face_image_bytes: Cropped face region (from face detector)
            
        Returns:
            Dictionary containing:
            - emotion_detected: bool
            - dominant_emotion: str (e.g., "happy", "neutral")
            - confidence: float (0 to 1)
            - all_emotions: Dict[str, float] (all class probabilities)
            - focus_state: str (mapped to focus categories)
        """
        if not TF_AVAILABLE:
            return self._get_empty_result("TensorFlow not available")
        
        if not self.model_loaded:
            logger.warning("Emotion detection model not loaded, attempting reload...")
            self._load_model()
            
            if not self.model_loaded:
                return self._get_empty_result("Model not loaded")
        
        try:
            # Preprocess face image
            preprocessed = self.preprocess_face(face_image_bytes)
            
            if preprocessed is None:
                return self._get_empty_result("Preprocessing failed")
            
            # Run inference
            predictions = self.model.predict(preprocessed, verbose=0)
            
            # Get probabilities for each emotion class
            probabilities = predictions[0]
            
            # Get dominant emotion
            dominant_idx = np.argmax(probabilities)
            dominant_emotion = self.EMOTION_CLASSES[dominant_idx]
            confidence = float(probabilities[dominant_idx])
            
            # Create emotion probability dictionary
            all_emotions = {
                emotion: float(prob) 
                for emotion, prob in zip(self.EMOTION_CLASSES, probabilities)
            }
            
            # Map to focus state
            focus_state = self.FOCUS_MAPPING.get(dominant_emotion, "unknown")
            
            result = {
                "emotion_detected": True,
                "dominant_emotion": dominant_emotion,
                "confidence": confidence,
                "all_emotions": all_emotions,
                "focus_state": focus_state
            }
            
            logger.info(f"😊 Emotion detected: {dominant_emotion} ({confidence:.2f})")
            return result
            
        except Exception as e:
            logger.error(f"Error in emotion detection: {e}")
            return self._get_empty_result(str(e))
    
    def is_positive_emotion(self, emotion: str) -> bool:
        """
        Check if emotion indicates positive engagement
        
        Args:
            emotion: Emotion label
            
        Returns:
            True if positive emotion
        """
        positive_emotions = ["happy", "surprise", "neutral"]
        return emotion in positive_emotions
    
    def is_distracted_emotion(self, emotion: str) -> bool:
        """
        Check if emotion indicates distraction
        
        Args:
            emotion: Emotion label
            
        Returns:
            True if distracted
        """
        distracted_emotions = ["angry", "fear", "disgust"]
        return emotion in distracted_emotions
    
    def calculate_engagement_score(self, all_emotions: Dict[str, float]) -> float:
        """
        Calculate engagement score based on emotion distribution
        
        Args:
            all_emotions: Dictionary of emotion probabilities
            
        Returns:
            Engagement score (0 to 1)
        """
        try:
            # Positive emotions contribute positively
            positive_score = (
                all_emotions.get("happy", 0) * 1.0 +
                all_emotions.get("neutral", 0) * 0.8 +
                all_emotions.get("surprise", 0) * 0.6
            )
            
            # Negative emotions reduce engagement
            negative_score = (
                all_emotions.get("sad", 0) * 0.3 +
                all_emotions.get("angry", 0) * 0.5 +
                all_emotions.get("fear", 0) * 0.4 +
                all_emotions.get("disgust", 0) * 0.4
            )
            
            engagement = positive_score - negative_score
            engagement = np.clip(engagement, 0.0, 1.0)
            
            return float(engagement)
            
        except Exception as e:
            logger.error(f"Error calculating engagement score: {e}")
            return 0.0
    
    def _get_empty_result(self, message: str = "") -> Dict:
        """Return empty result when detection fails"""
        return {
            "emotion_detected": False,
            "dominant_emotion": "unknown",
            "confidence": 0.0,
            "all_emotions": {emotion: 0.0 for emotion in self.EMOTION_CLASSES},
            "focus_state": "unknown",
            "message": message
        }
    
    def get_status(self) -> Dict:
        """Get emotion detector status"""
        return {
            "model_loaded": self.model_loaded,
            "model_path": self.model_path,
            "tensorflow_available": TF_AVAILABLE,
            "model_type": "Keras CNN (H5)",
            "emotion_classes": self.EMOTION_CLASSES,
            "input_shape": self.input_shape,
            "focus_mapping": self.FOCUS_MAPPING
        }


# Global instance
emotion_detector = EmotionDetector()
