"""
FocusFlow Backend Configuration
Handles all application settings and environment variables
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings and configuration"""
    
    # Application
    APP_NAME: str = "FocusFlow"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # Database Configuration
    # UPDATE THESE VALUES WITH YOUR MYSQL CREDENTIALS
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_USER: str = "root"
    DB_PASSWORD: str = "arav"  # CHANGE THIS
    DB_NAME: str = "focusflow"

    # ML Settings
    MODEL_PATH: str = "models/emotion_model.h5"
    GEMINI_API_KEY: str = ""
    YOUTUBE_API_KEY: str = ""

    @property
    def DATABASE_URL(self) -> str:
        """Construct database URL from components"""
        return f"mysql+mysqlconnector://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
    
    # JWT Configuration
    # IMPORTANT: Generate a secure secret key for production
    # You can generate one using: openssl rand -hex 32
    SECRET_KEY: str = "7a9c8d5e1f3b2a4c6d8e0f1a3b5c7d9e2f4a6b8c0d1e3f5a7b9c1d3e5f7a9b2"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_HOURS: int = 24
    
    # CORS Configuration
    CORS_ORIGINS: list = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "http://127.0.0.1:8000",
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "null"
    ]
    
    # Study Technique Configurations (in seconds)
    POMODORO_STUDY: int = 25 * 60  # 25 minutes
    POMODORO_BREAK: int = 5 * 60   # 5 minutes
    
    TECHNIQUE_52_17_STUDY: int = 52 * 60  # 52 minutes
    TECHNIQUE_52_17_BREAK: int = 17 * 60  # 17 minutes
    
    STUDY_SPRINT_STUDY: int = 15 * 60  # 15 minutes
    STUDY_SPRINT_BREAK: int = 5 * 60   # 5 minutes
    
    # Distraction Detection Thresholds (in seconds)
    MOUSE_INACTIVITY_THRESHOLD: int = 60      # 1 minute
    KEYBOARD_INACTIVITY_THRESHOLD: int = 60   # 1 minute
    CAMERA_ABSENCE_THRESHOLD: int = 120       # 2 minutes
    LONG_PAUSE_THRESHOLD: int = 180           # 3 minutes
    
    # Phase-2 ML Integration Thresholds (Placeholders)
    FACE_ABSENCE_THRESHOLD: int = 90          # 1.5 minutes
    EMOTION_CONFIDENCE_THRESHOLD: float = 0.7  # 70% confidence
    
    # Focus Score Weights
    IDLE_TIME_WEIGHT: float = 0.40      # 40%
    DISTRACTION_WEIGHT: float = 0.30    # 30%
    CONSISTENCY_WEIGHT: float = 0.20    # 20%
    CAMERA_WEIGHT: float = 0.10         # 10%
    
    # Phase-2: Additional weights for ML features
    FACE_PRESENCE_WEIGHT: float = 0.05  # Will be used in Phase-2
    EMOTION_WEIGHT: float = 0.05        # Will be used in Phase-2
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()


# Study technique mapping
STUDY_TECHNIQUES = {
    "pomodoro": {
        "name": "Pomodoro",
        "study_duration": settings.POMODORO_STUDY,
        "break_duration": settings.POMODORO_BREAK,
        "description": "25 minutes study, 5 minutes break"
    },
    "52-17": {
        "name": "52-17 Technique",
        "study_duration": settings.TECHNIQUE_52_17_STUDY,
        "break_duration": settings.TECHNIQUE_52_17_BREAK,
        "description": "52 minutes study, 17 minutes break"
    },
    "study-sprint": {
        "name": "Study Sprint",
        "study_duration": settings.STUDY_SPRINT_STUDY,
        "break_duration": settings.STUDY_SPRINT_BREAK,
        "description": "15 minutes study, 5 minutes break"
    },
    "flowtime": {
        "name": "Flowtime",
        "study_duration": None,  # User-defined
        "break_duration": None,  # User-defined
        "description": "Study until you need a break"
    }
}


# Study mode configurations
STUDY_MODES = {
    "screen": {
        "name": "Screen Study",
        "track_mouse": True,
        "track_keyboard": True,
        "track_tabs": True,
        "track_camera": True,
        "description": "For studying on computer/tablet"
    },
    "book": {
        "name": "Book/Notes Study",
        "track_mouse": False,  # Ignore mouse inactivity
        "track_keyboard": False,  # Ignore keyboard inactivity
        "track_tabs": True,
        "track_camera": True,
        "description": "For reading books or taking notes"
    }
}


# User state definitions
USER_STATES = {
    "focused": "Actively engaged in studying",
    "reading": "Low activity but acceptable (reading mode)",
    "distracted": "High inactivity or frequent interruptions",
    "away": "No presence detected"
}


# Phase-2: Emotion categories for future ML integration
EMOTION_CATEGORIES = {
    "neutral": "Neutral expression",
    "focused": "Concentrated and engaged",
    "distracted": "Looking away or unfocused",
    "fatigued": "Tired or drowsy"
}


def get_technique_config(technique: str) -> dict:
    """Get configuration for a study technique"""
    return STUDY_TECHNIQUES.get(technique, STUDY_TECHNIQUES["pomodoro"])


def get_mode_config(mode: str) -> dict:
    """Get configuration for a study mode"""
    return STUDY_MODES.get(mode, STUDY_MODES["screen"])
