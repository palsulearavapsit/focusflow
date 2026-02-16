"""
FocusFlow Pydantic Models (Schemas)
Data validation and serialization models
"""

from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, Literal, List
from datetime import datetime
from enum import Enum


# Enums
class UserRole(str, Enum):
    """User role enumeration"""
    STUDENT = "student"
    ADMIN = "admin"
    TEACHER = "teacher"


class StudyTechnique(str, Enum):
    """Study technique enumeration"""
    POMODORO = "pomodoro"
    TECHNIQUE_52_17 = "52-17"
    STUDY_SPRINT = "study-sprint"
    FLOWTIME = "flowtime"


class StudyMode(str, Enum):
    """Study mode enumeration"""
    SCREEN = "screen"
    BOOK = "book"


class UserState(str, Enum):
    """User state during study session"""
    FOCUSED = "focused"
    READING = "reading"
    DISTRACTED = "distracted"
    AWAY = "away"


# Request Models
class UserSignupRequest(BaseModel):
    """User registration request"""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=100)
    role: UserRole = UserRole.STUDENT
    
    @validator('username')
    def username_alphanumeric(cls, v):
        """Validate username is alphanumeric"""
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('Username must be alphanumeric (underscores and hyphens allowed)')
        return v


class UserLoginRequest(BaseModel):
    """User login request"""
    email: EmailStr
    password: str


class SessionStartRequest(BaseModel):
    """
    Start study session request
    
    Note: When camera_enabled=True, all computer vision features are enabled:
    - Face detection (detect_face.tflite)
    - Eye tracking (track_eye.task)
    - Emotion detection (detect_emotion.h5)
    """
    technique: StudyTechnique
    study_mode: StudyMode
    camera_enabled: bool = False  # When True, all CV models are enabled
    classroom_id: Optional[int] = None


class SessionEndRequest(BaseModel):
    """End study session request"""
    duration: int = Field(..., ge=0, description="Duration in seconds")
    distractions: int = Field(default=0, ge=0)
    mouse_inactive_time: int = Field(default=0, ge=0)
    keyboard_inactive_time: int = Field(default=0, ge=0)
    tab_switches: int = Field(default=0, ge=0)
    camera_absence_time: int = Field(default=0, ge=0)
    face_absence_time: int = Field(default=0, ge=0)  # Phase-2
    dominant_emotion: str = Field(default="UNKNOWN")  # Phase-2
    emotion_confidence: float = Field(default=0.0, ge=0.0, le=1.0)  # Phase-2
    user_state: UserState = UserState.FOCUSED


# Response Models
class UserResponse(BaseModel):
    """User response model"""
    id: int
    username: str
    email: str
    role: UserRole
    created_at: datetime
    
    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """JWT token response"""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class SessionResponse(BaseModel):
    """Study session response"""
    id: int
    user_id: int
    technique: StudyTechnique
    study_mode: StudyMode
    camera_enabled: bool  # When True, all CV features were active
    duration: int
    distractions: int
    focus_score: float
    mouse_inactive_time: int
    keyboard_inactive_time: int
    tab_switches: int
    camera_absence_time: int
    face_absence_time: int
    dominant_emotion: str
    emotion_confidence: float
    user_state: UserState
    recommended_technique: Optional[str]
    timestamp: datetime
    
    class Config:
        from_attributes = True


class SessionSummaryResponse(BaseModel):
    """Session summary for frontend display"""
    session_id: int
    technique: str
    study_mode: str
    duration_minutes: int
    focus_score: float
    distractions: int
    user_state: str
    camera_enabled: bool  # When True, all CV features were active
    dominant_emotion: str
    recommended_technique: Optional[str]
    timestamp: datetime
    
    # Detailed metrics
    idle_time_percentage: float
    tab_switches: int
    camera_absence_minutes: int
    face_absence_minutes: int  # Phase-2


class AdminStatisticsResponse(BaseModel):
    """Admin dashboard statistics"""
    total_students: int
    total_sessions: int
    overall_avg_focus_score: Optional[float]
    total_study_time_all_users: int
    sessions_with_camera_enabled: int
    most_popular_technique: Optional[str]
    most_popular_mode: Optional[str]


class UserStatisticsResponse(BaseModel):
    """User statistics for admin view"""
    user_id: int
    username: str
    email: str
    total_sessions: int
    total_study_time: int
    avg_focus_score: Optional[float]
    total_distractions: int
    avg_distractions_per_session: Optional[float]
    most_used_technique: Optional[str]
    sessions_with_camera: int


class MessageResponse(BaseModel):
    """Generic message response"""
    message: str
    success: bool = True


class ErrorResponse(BaseModel):
    """Error response"""
    detail: str
    error_code: Optional[str] = None


# Phase-2 Models (Placeholders for ML Integration)
class FaceDetectionResult(BaseModel):
    """
    Face detection result model
    Phase-2: Will be populated by pre-trained face detection model
    """
    face_detected: bool = False
    face_count: int = 0
    confidence: float = 0.0
    bounding_box: Optional[List[int]] = None  # [x, y, w, h]
    timestamp: datetime = Field(default_factory=datetime.now)
    # Will be populated by MediaPipe/Face-API.js in Phase-2


class EyeDetectionResult(BaseModel):
    """
    Eye detection result model
    Phase-2: Will be populated by custom eye tracking model
    """
    eyes_detected: bool = False
    eye_count: int = 0
    confidence: float = 0.0
    timestamp: datetime = Field(default_factory=datetime.now)


class EmotionDetectionResult(BaseModel):
    """
    Emotion detection result model
    Updated for three-model pipeline integration
    """
    emotion_detected: bool = False
    emotion: str = "unknown"  # angry, disgust, fear, happy, sad, surprise, neutral
    confidence: float = 0.0
    timestamp: datetime = Field(default_factory=datetime.now)


class CompleteAnalysisResult(BaseModel):
    """
    Complete frame analysis result from all three models
    """
    success: bool
    face_detected: bool
    face_count: int
    processing_time_ms: float
    timestamp: datetime = Field(default_factory=datetime.now)


class FocusMetricsResult(BaseModel):
    """
    Focus and attention metrics extracted from pipeline
    """
    face_present: bool
    multiple_faces: bool
    eyes_open: bool
    blink_detected: bool
    attention_score: float
    gaze_centered: bool
    emotion_state: str
    engagement_score: float
    overall_focus_score: float
    timestamp: datetime = Field(default_factory=datetime.now)


class MLFeaturesRequest(BaseModel):
    """
    ML features for enhanced session tracking
    Phase-2: Will include actual face and emotion data
    """
    face_presence_ratio: float = Field(default=0.0, ge=0.0, le=1.0)
    avg_emotion_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    emotion_stability_score: float = Field(default=0.0, ge=0.0, le=1.0)
    

    # Note: Currently returns default values
    # Will be calculated from actual ML model outputs in Phase-2


# Classroom Models
class ClassroomCreateRequest(BaseModel):
    """Request to create a classroom"""
    name: str = Field(..., min_length=3, max_length=100)

class JoinClassroomRequest(BaseModel):
    """Request to join a classroom"""
    code: str = Field(..., min_length=10, max_length=10)

class ClassroomResponse(BaseModel):
    """Classroom response model"""
    id: int
    name: str
    code: str
    teacher_id: int
    teacher_name: Optional[str] = None
    created_at: datetime
    student_count: Optional[int] = 0

class ClassroomStudentStats(BaseModel):
    """Stats for a student in a specific classroom"""
    student_id: int
    username: str
    role: Optional[str] = "student"
    total_sessions: int
    total_study_time: int
    avg_focus_score: float

class ClassroomDetailsResponse(BaseModel):
    """Detailed classroom view with student stats"""
    classroom: ClassroomResponse
    students: List[ClassroomStudentStats]

class UpdateRoleRequest(BaseModel):
    """Request to update a student's role"""
    role: str = Field(..., pattern="^(student|representative)$")


class UserSystemRoleUpdate(BaseModel):
    """Request to update a user's system role (admin)"""
    role: UserRole
