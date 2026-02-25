"""
Face Detection Service - TFLite Model Integration

This service handles face detection using a lightweight TFLite model.
Model: detect_face.tflite

Responsibilities:
- Detect and localize faces in video frames
- Return bounding box coordinates for detected faces
- Optimized for real-time CPU inference
- Runs first in the pipeline to provide clean face regions

Output:
- face_detected: bool
- face_count: int
- bounding_boxes: List of [x, y, width, height]
- confidence_scores: List of confidence values
"""

import cv2
import numpy as np
import tensorflow as tf
import os
import logging
from typing import Dict, List, Tuple, Optional

logger = logging.getLogger(__name__)


class FaceDetector:
    """
    Face Detection using TFLite model
    
    This is the first stage of the computer vision pipeline.
    It detects faces and provides bounding boxes for downstream models.
    """
    
    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize the face detector
        
        Args:
            model_path: Path to detect_face.tflite model
        """
        if model_path is None:
            model_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                "models", "face_detection", "detect_face.tflite"
            )
        
        self.model_path = model_path
        self.interpreter = None
        self.input_details = None
        self.output_details = None
        self.model_loaded = False
        
        # Load model on initialization
        self._load_model()
    
    def _load_model(self):
        """Load the TFLite face detection model"""
        try:
            if not os.path.exists(self.model_path):
                logger.error(f"❌ Face detection model not found at {self.model_path}")
                return
            
            # Initialize TFLite interpreter
            self.interpreter = tf.lite.Interpreter(model_path=self.model_path)
            self.interpreter.allocate_tensors()
            
            # Get input and output details
            self.input_details = self.interpreter.get_input_details()
            self.output_details = self.interpreter.get_output_details()
            
            self.model_loaded = True
            logger.info(f"✅ Face detection model loaded from {self.model_path}")
            logger.info(f"   Input shape: {self.input_details[0]['shape']}")
            logger.info(f"   Output shape: {self.output_details[0]['shape']}")
            
        except Exception as e:
            logger.error(f"❌ Failed to load face detection model: {e}")
            self.model_loaded = False
    
    def preprocess_image(self, image_bytes: bytes) -> Optional[np.ndarray]:
        """
        Preprocess image for face detection
        
        Args:
            image_bytes: Raw image bytes
            
        Returns:
            Preprocessed image array or None if error
        """
        try:
            # Convert bytes to numpy array
            nparr = np.frombuffer(image_bytes, np.uint8)
            
            # Decode image
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if img is None:
                logger.error("Failed to decode image")
                return None
            
            # Convert BGR to RGB (TFLite models typically expect RGB)
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            
            # Get input shape from model
            input_shape = self.input_details[0]['shape']
            height, width = input_shape[1], input_shape[2]
            
            # Resize image to model input size
            img_resized = cv2.resize(img_rgb, (width, height))
            
            # Normalize to [0, 1] if model expects float input
            if self.input_details[0]['dtype'] == np.float32:
                img_resized = img_resized.astype(np.float32) / 255.0
            
            # Add batch dimension
            img_input = np.expand_dims(img_resized, axis=0)
            
            return img_input, img
            
        except Exception as e:
            logger.error(f"Error preprocessing image: {e}")
            return None, None
    
    def detect_faces(self, image_bytes: bytes) -> Dict:
        """
        Detect faces in image
        
        This is the main entry point for face detection.
        
        Args:
            image_bytes: Raw image bytes from camera/upload
            
        Returns:
            Dictionary containing:
            - face_detected: bool
            - face_count: int
            - bounding_boxes: List of [x, y, w, h]
            - confidence_scores: List of confidence values
            - original_image_shape: Tuple of (height, width, channels)
        """
        if not self.model_loaded:
            logger.warning("Face detection model not loaded, attempting reload...")
            self._load_model()
            
            if not self.model_loaded:
                return self._get_empty_result()
        
        try:
            # Preprocess image
            preprocessed_result = self.preprocess_image(image_bytes)
            
            if preprocessed_result is None:
                return self._get_empty_result()
            
            img_input, original_img = preprocessed_result
            
            if img_input is None:
                return self._get_empty_result()
            
            # Run inference
            print("\n" + "="*20 + " INFERENCE START " + "="*20)
            self.interpreter.set_tensor(self.input_details[0]['index'], img_input)
            self.interpreter.invoke()
            print("="*20 + " INFERENCE END   " + "="*20 + "\n")
            
            # Get output tensors
            # Note: Output format depends on the specific TFLite model
            # Common formats: [num_detections, boxes, scores, classes]
            boxes = self.interpreter.get_tensor(self.output_details[0]['index'])
            scores = self.interpreter.get_tensor(self.output_details[1]['index']) if len(self.output_details) > 1 else None
            
            # Parse detections
            bounding_boxes, confidence_scores = self._parse_detections(
                boxes, scores, original_img.shape
            )
            
            result = {
                "face_detected": len(bounding_boxes) > 0,
                "face_count": len(bounding_boxes),
                "bounding_boxes": bounding_boxes,
                "confidence_scores": confidence_scores,
                "original_image_shape": original_img.shape
            }
            
            logger.info(f"📸 Face detection: {len(bounding_boxes)} face(s) detected")
            return result
            
        except Exception as e:
            logger.error(f"Error in face detection: {e}")
            return self._get_empty_result()
    
    def _parse_detections(
        self, 
        boxes: np.ndarray, 
        scores: Optional[np.ndarray],
        image_shape: Tuple[int, int, int],
        confidence_threshold: float = 0.2
    ) -> Tuple[List, List]:
        """
        Parse detection outputs into bounding boxes and scores
        """
        bounding_boxes = []
        confidence_scores = []
        
        try:
            # Handle different output formats
            if len(boxes.shape) == 3:
                boxes = boxes[0]  # [N, 4 or 16]
            
            if scores is not None and len(scores.shape) == 3:
                scores = scores[0]  # [N, 1]
            
            height, width = image_shape[:2]
            
            # Debug: Check if scores need sigmoid (if they are logits)
            if scores is not None:
                max_score = np.max(scores)
                min_score = np.min(scores)
                print(f"DEBUG: Face scores range: [{min_score:.4f}, {max_score:.4f}]")
                if len(boxes) > 0:
                    print(f"DEBUG: First raw box: {boxes[0][:4]}")
                
                # If max score is > 5 or < 0, it's likely logits
                needs_sigmoid = max_score > 1.0 or min_score < 0
            else:
                needs_sigmoid = False
            
            for i, box in enumerate(boxes):
                # Get confidence score
                raw_conf = scores[i] if scores is not None else 1.0
                
                # Handle array score [val]
                if isinstance(raw_conf, (np.ndarray, list)):
                    raw_conf = raw_conf[0]
                
                # Apply sigmoid if logit
                if needs_sigmoid:
                    conf = 1.0 / (1.0 + np.exp(-float(raw_conf)))
                else:
                    conf = float(raw_conf)
                
                # Filter by confidence threshold
                if conf < confidence_threshold:
                    continue
                
                # Convert normalized coordinates to pixel coordinates
                # Box format: [ymin, xmin, ymax, xmax] (normalized 0-1)
                ymin, xmin, ymax, xmax = box[:4]
                
                # Clip to [0, 1]
                ymin = max(0.0, min(1.0, float(ymin)))
                xmin = max(0.0, min(1.0, float(xmin)))
                ymax = max(0.0, min(1.0, float(ymax)))
                xmax = max(0.0, min(1.0, float(xmax)))

                if (ymax - ymin) < 0.05 or (xmax - xmin) < 0.05:
                    continue # Too small

                x = int(xmin * width)
                y = int(ymin * height)
                w = int((xmax - xmin) * width)
                h = int((ymax - ymin) * height)
                
                bounding_boxes.append([x, y, w, h])
                confidence_scores.append(float(conf))
            
            # Sort by confidence
            if bounding_boxes:
                combined = sorted(zip(confidence_scores, bounding_boxes), reverse=True, key=lambda x: x[0])
                confidence_scores = [c for c, b in combined]
                bounding_boxes = [b for c, b in combined]

        except Exception as e:
            logger.error(f"Error parsing detections: {e}")
        
        return bounding_boxes, confidence_scores
    
    def crop_face_region(
        self, 
        image_bytes: bytes, 
        bounding_box: List[int],
        padding: float = 0.1
    ) -> Optional[bytes]:
        """
        Crop face region from image for downstream models
        
        Args:
            image_bytes: Original image bytes
            bounding_box: [x, y, w, h]
            padding: Extra padding around face (10% by default)
            
        Returns:
            Cropped face image as bytes
        """
        try:
            # Decode image
            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if img is None:
                return None
            
            # Extract box coordinates
            x, y, w, h = bounding_box
            
            # Add padding
            pad_w = int(w * padding)
            pad_h = int(h * padding)
            
            x1 = max(0, x - pad_w)
            y1 = max(0, y - pad_h)
            x2 = min(img.shape[1], x + w + pad_w)
            y2 = min(img.shape[0], y + h + pad_h)
            
            # Crop face region
            face_roi = img[y1:y2, x1:x2]
            
            # Encode back to bytes
            _, buffer = cv2.imencode('.jpg', face_roi)
            return buffer.tobytes()
            
        except Exception as e:
            logger.error(f"Error cropping face region: {e}")
            return None
    
    def _get_empty_result(self) -> Dict:
        """Return empty result when detection fails"""
        return {
            "face_detected": False,
            "face_count": 0,
            "bounding_boxes": [],
            "confidence_scores": [],
            "original_image_shape": None
        }
    
    def get_status(self) -> Dict:
        """Get face detector status"""
        return {
            "model_loaded": self.model_loaded,
            "model_path": self.model_path,
            "model_type": "TFLite Face Detection",
            "optimized_for": "Real-time CPU inference"
        }


# Global instance
face_detector = FaceDetector()
