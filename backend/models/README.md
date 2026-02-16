# Machine Learning Models

This directory contains the pre-trained models required for FocusFlow's computer vision features.

## Required Models

Please download the following models and place them in their respective subdirectories:

1.  **Face Detection** (`face_detection/detect_face.tflite`)
    *   **Source**: TensorFlow Face Detection Model
    *   **Filename**: `detect_face.tflite`
    *   **Path**: `backend/models/face_detection/detect_face.tflite`

2.  **Eye Tracking** (`eye_tracking/track_eye.task`)
    *   **Source**: Mediapipe Iris Tracking Model (or custom model)
    *   **Filename**: `track_eye.task`
    *   **Path**: `backend/models/eye_tracking/track_eye.task`

3.  **Emotion Detection** (`emotion_detection/detect_emotion.h5`)
    *   **Source**: Custom emotion classification model (Keras/TensorFlow)
    *   **Filename**: `detect_emotion.h5`
    *   **Path**: `backend/models/emotion_detection/detect_emotion.h5`

## Note

Ensure the directory structure matches exactly as described above for the application to load the models correctly.
