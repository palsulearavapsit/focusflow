---
title: Focusflow Backend
emoji: 🚀
colorFrom: indigo
colorTo: blue
sdk: docker
pinned: false
---

# FocusFlow

FocusFlow is an intelligent study assistant application that uses computer vision to track user focus and engagement.

## Architecture

- **Backend**: Python FastAPI with Machine Learning models (TensorFlow/Mediapipe)
- **Frontend**: HTML/JS/CSS with Bootstrap and Chart.js
- **Database**: MySQL

## Setup & Installation

### Prerequisites

- Python 3.8+
- MySQL Server

### 1. Set up Virtual Environment

The backend includes a `venv` directory. Activate it:

**Windows:**
```bash
cd backend
venv\Scripts\activate
```

**macOS/Linux:**
```bash
cd backend
source venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r backend/requirements.txt
```

### 3. Configure Environment

Review the `.env` file in the `backend/` directory and update the database credentials and API keys as needed.

### 4. Download ML Models

The application requires pre-trained models. Place them in the following directories:

- `backend/models/face_detection/detect_face.tflite`
- `backend/models/eye_tracking/track_eye.task`
- `backend/models/emotion_detection/detect_emotion.h5`

See `backend/models/README.md` (if available) or documentation for download links.

## Running the Application

Use the unified launcher script:

```bash
python run.py
```

This will verify dependencies, check database connection, and start both the backend API server (port 8000) and frontend server (port 3000).

## Services

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
