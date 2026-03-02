# Machine Learning Models

This directory contains the pre-trained models required for FocusFlow's computer vision features.

## Required Models

Please download the following models and place them in their respective subdirectories:

1. **Face Detection** (`face_detection/detect_face.tflite`)
   - **Dataset**: Kaggle Face Detection Dataset
   - **Source**: https://www.kaggle.com/datasets/fareselmenshawii/face-detection-dataset
   - **Format**: TensorFlow Lite (.tflite)
   - **Filename**: `detect_face.tflite`
   - **Path**: `backend/models/face_detection/detect_face.tflite`
   - **Task**: Bounding box face localization
   - **Algorithm Used**: CNN-based Object Detection Architecture with bounding box regression and classification loss, optimized and converted to TensorFlow Lite for real-time inference.

2. **Eye Tracking** (`eye_tracking/track_eye.task`)
   - **Dataset**: Cropped eye-region samples derived from Kaggle Face Detection Dataset
   - **Source**: https://www.kaggle.com/datasets/fareselmenshawii/face-detection-dataset
   - **Format**: MediaPipe Task (.task)
   - **Filename**: `track_eye.task`
   - **Path**: `backend/models/eye_tracking/track_eye.task`
   - **Task**: Iris landmark detection and gaze direction estimation
   - **Algorithm Used**: Multi-stage Convolutional Neural Network (CNN) for eye-region detection and landmark regression, with temporal smoothing applied for stable gaze estimation.

3. **Emotion Detection** (`emotion_detection/detect_emotion.h5`)
   - **Dataset**: Kaggle Facial Expression Dataset
   - **Source**: https://www.kaggle.com/datasets/aadityasinghal/facial-expression-dataset
   - **Format**: Keras (.h5)
   - **Filename**: `detect_emotion.h5`
   - **Path**: `backend/models/emotion_detection/detect_emotion.h5`
   - **Task**: Multi-class emotion classification
   - **Algorithm Used**: Deep Convolutional Neural Network (CNN) with Batch Normalization and Dropout, trained using Categorical Cross-Entropy loss and Adam optimizer with Softmax output layer.

## Note

Ensure the directory structure matches exactly as described above for the application to load the models correctly.
