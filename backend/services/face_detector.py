"""
FocusFlow Face Detector Service
Uses OpenCV DNN (primary) with TFLite + Haar cascade fallbacks.
"""

import logging
import os
import numpy as np
from typing import Dict, List, Optional
import cv2

logger = logging.getLogger(__name__)

# ─── Try TFLite ───────────────────────────────────────────────────────────────
try:
    import tensorflow as tf
    TFLITE_AVAILABLE = True
except ImportError:
    TFLITE_AVAILABLE = False
    logger.warning("⚠️ TensorFlow not available. Face detection disabled.")


class FaceDetector:
    """
    Face detector using multiple methods in priority order:
    1. TFLite BlazeFace model (detect_face.tflite)
    2. OpenCV Haar Cascade fallback (always available)
    """

    MODEL_FILENAME = "detect_face.tflite"

    def __init__(self):
        self.model_loaded = False
        self.interpreter = None
        self.input_size = 128   # BlazeFace default
        self.input_details = None
        self.output_details = None
        self._load_model()

    def _load_model(self):
        """Load the TFLite BlazeFace model"""
        model_path = os.path.abspath(os.path.join(
            os.path.dirname(__file__), "..", "models", "face_detection", self.MODEL_FILENAME
        ))

        if not os.path.exists(model_path):
            logger.warning(f"⚠️ Face detection model not found at: {model_path} — using Haar cascade fallback")
            return

        if not TFLITE_AVAILABLE:
            logger.warning("⚠️ TFLite not available — using Haar cascade fallback")
            return

        try:
            self.interpreter = tf.lite.Interpreter(model_path=model_path)
            self.interpreter.allocate_tensors()
            self.input_details  = self.interpreter.get_input_details()
            self.output_details = self.interpreter.get_output_details()

            # Detect input size from model
            shape = self.input_details[0]['shape']   # [1, H, W, C]
            self.input_size = shape[1]

            self.model_loaded = True
            logger.info(f"✅ Face detection model loaded (input: {self.input_size}x{self.input_size})")
        except Exception as e:
            logger.error(f"❌ Failed to load face detection model: {e}")
            logger.info("   → Will use OpenCV Haar cascade fallback")

    # ─── Public API ──────────────────────────────────────────────────────────

    def detect_faces(self, frame_bytes: bytes) -> Dict:
        """
        Detect faces in image bytes.

        Returns:
            {
                "face_detected": bool,
                "face_count":    int,
                "bounding_boxes":    [[x, y, w, h], ...],
                "confidence_scores": [float, ...]
            }
        """
        if self.model_loaded:
            result = self._detect_tflite(frame_bytes)
            if result["face_count"] > 0:
                return result
            # Fall through to Haar if TFLite finds nothing
            # (sometimes TFLite is picky about lighting/angle)

        return self._detect_haar(frame_bytes)

    def crop_face_region(self, frame_bytes: bytes, bbox: List[int]) -> Optional[bytes]:
        """Crop a face region [x, y, w, h] from image bytes with padding."""
        try:
            nparr = np.frombuffer(frame_bytes, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if frame is None:
                return None

            x, y, w, h = bbox
            pad = 15
            x1 = max(0, x - pad)
            y1 = max(0, y - pad)
            x2 = min(frame.shape[1], x + w + pad)
            y2 = min(frame.shape[0], y + h + pad)

            crop = frame[y1:y2, x1:x2]
            if crop.size == 0:
                return None

            _, buf = cv2.imencode('.jpg', crop)
            return buf.tobytes()
        except Exception as e:
            logger.error(f"❌ Face crop error: {e}")
            return None

    def get_status(self) -> Dict:
        return {
            "model_loaded":       self.model_loaded,
            "model_file":         self.MODEL_FILENAME,
            "fallback_available": True,   # Haar is always available via OpenCV
            "description":        "TFLite BlazeFace + OpenCV Haar cascade fallback"
        }

    # ─── Private Detection Methods ────────────────────────────────────────────

    def _detect_tflite(self, frame_bytes: bytes) -> Dict:
        """Run TFLite BlazeFace inference."""
        try:
            nparr = np.frombuffer(frame_bytes, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if frame is None:
                return self._empty()

            h, w = frame.shape[:2]
            sz = self.input_size

            # Pre-process: resize + normalize to [-1, 1] (BlazeFace standard)
            resized = cv2.resize(frame, (sz, sz))
            rgb     = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
            inp     = (rgb.astype(np.float32) - 127.5) / 127.5
            inp     = np.expand_dims(inp, axis=0)

            self.interpreter.set_tensor(self.input_details[0]['index'], inp)
            self.interpreter.invoke()

            # BlazeFace outputs: regressors [1,896,16] + classificators [1,896,1]
            # Try to find score output (classificator) automatically
            scores_tensor = None
            boxes_tensor  = None

            for detail in self.output_details:
                shape = detail['shape']
                if len(shape) == 3 and shape[2] == 1:
                    scores_tensor = self.interpreter.get_tensor(detail['index'])[0, :, 0]
                elif len(shape) == 3 and shape[2] >= 4:
                    boxes_tensor  = self.interpreter.get_tensor(detail['index'])[0]

            if scores_tensor is None or boxes_tensor is None:
                # Fallback: use first two outputs generically
                out0 = self.interpreter.get_tensor(self.output_details[0]['index'])
                out1 = self.interpreter.get_tensor(self.output_details[1]['index'])
                if out0.shape[-1] == 1:
                    scores_tensor = out0[0, :, 0] if out0.ndim == 3 else out0[0]
                    boxes_tensor  = out1[0]        if out1.ndim == 3 else out1
                else:
                    scores_tensor = out1[0, :, 0] if out1.ndim == 3 else out1[0]
                    boxes_tensor  = out0[0]        if out0.ndim == 3 else out0

            THRESHOLD = 0.65
            bboxes, confs = [], []

            for i, score in enumerate(scores_tensor):
                # Safe sigmoid
                if score < -500:
                    score = 0.0
                elif score > 500:
                    score = 1.0
                elif score < -10 or score > 10:
                    score = 1.0 / (1.0 + np.exp(-float(score)))

                if score >= THRESHOLD and i < len(boxes_tensor):
                    box = boxes_tensor[i]
                    # BlazeFace box: [ymin, xmin, ymax, xmax] normalized to input size
                    # Convert to [x, y, w, h] in original pixel coords
                    if len(box) >= 4:
                        cy, cx, bh, bw = box[0], box[1], box[2], box[3]
                        # Some variants: [ymin, xmin, ymax, xmax]
                        if bh > 1.0:  # Already absolute → treat as [ymin,xmin,ymax,xmax]
                            ymin, xmin, ymax, xmax = cy/sz, cx/sz, bh/sz, bw/sz
                        else:
                            # Center-form: [cy, cx, h, w] normalized 0-1
                            ymin = max(0, cy - bh/2)
                            xmin = max(0, cx - bw/2)
                            ymax = min(1, cy + bh/2)
                            xmax = min(1, cx + bw/2)

                        px = int(xmin * w)
                        py = int(ymin * h)
                        pw = int((xmax - xmin) * w)
                        ph = int((ymax - ymin) * h)

                        if pw > 10 and ph > 10:
                            bboxes.append([px, py, pw, ph])
                            confs.append(float(score))

            if bboxes:
                # Apply NMS to merge overlapping boxes
                indices = cv2.dnn.NMSBoxes(bboxes, confs, score_threshold=0.5, nms_threshold=0.4)
                if len(indices) > 0:
                    flat_idx = [i[0] if isinstance(i, (list, np.ndarray)) else int(i) for i in indices]
                    bboxes = [bboxes[i] for i in flat_idx]
                    confs  = [confs[i]  for i in flat_idx]

                logger.info(f"📸 TFLite: {len(bboxes)} face(s) detected")
                return {"face_detected": True, "face_count": len(bboxes),
                        "bounding_boxes": bboxes, "confidence_scores": confs}

            return self._empty()

        except Exception as e:
            logger.error(f"❌ TFLite face detection error: {e}")
            return self._empty()

    def _detect_haar(self, frame_bytes: bytes) -> Dict:
        """Reliable OpenCV Haar cascade fallback."""
        try:
            nparr = np.frombuffer(frame_bytes, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if frame is None:
                return self._empty()

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            # Enhance contrast for better detection
            gray = cv2.equalizeHist(gray)

            cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            cascade = cv2.CascadeClassifier(cascade_path)

            faces = cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=4,
                minSize=(60, 60),
                flags=cv2.CASCADE_SCALE_IMAGE
            )

            if len(faces) == 0:
                return self._empty()

            # Apply NMS to remove overlapping boxes
            faces_list = [[int(x), int(y), int(w), int(h)] for x, y, w, h in faces]
            scores     = [1.0] * len(faces_list)

            # cv2.dnn.NMSBoxes expects (x,y,w,h), scores, score_thresh, nms_thresh
            indices = cv2.dnn.NMSBoxes(faces_list, scores, score_threshold=0.3, nms_threshold=0.4)
            if len(indices) == 0:
                return self._empty()

            # Flatten indices (OpenCV returns nested list on some versions)
            flat_idx = [i[0] if isinstance(i, (list, np.ndarray)) else int(i) for i in indices]

            bboxes = [faces_list[i] for i in flat_idx]
            confs  = [0.92] * len(bboxes)

            logger.info(f"📸 Haar: {len(bboxes)} face(s) detected")
            return {
                "face_detected":     True,
                "face_count":        len(bboxes),
                "bounding_boxes":    bboxes,
                "confidence_scores": confs
            }
        except Exception as e:
            logger.error(f"❌ Haar cascade error: {e}")
            return self._empty()

    def _empty(self) -> Dict:
        return {
            "face_detected":     False,
            "face_count":        0,
            "bounding_boxes":    [],
            "confidence_scores": []
        }


# Global singleton
face_detector = FaceDetector()
