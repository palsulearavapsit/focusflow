"""
FocusFlow - Smart Study Assistant Backend
Main FastAPI Application

A production-ready study assistant application with:
- JWT authentication
- Role-based access control
- Study session management
- Focus tracking and scoring
- Admin dashboard
- Phase-2 ready for ML integration
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from config import settings
from database import db
from routes import auth_routes, session_routes, admin_routes, ml_routes, classroom_routes, tools_routes
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description="Backend API for FocusFlow Study Assistant",
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_routes.router)
app.include_router(session_routes.router)
app.include_router(admin_routes.router)
app.include_router(ml_routes.router)
app.include_router(classroom_routes.router)
app.include_router(tools_routes.router, prefix="/api/tools", tags=["Tools"])


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint - API information"""
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "message": "Welcome to FocusFlow API",
        "docs": "/docs",
        "redoc": "/redoc"
    }


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    db_status = db.test_connection()
    
    return {
        "status": "healthy" if db_status else "unhealthy",
        "database": "connected" if db_status else "disconnected",
        "version": settings.APP_VERSION
    }


# Configuration endpoint
@app.get("/api/config")
async def get_config():
    """
    Get public configuration
    Returns study techniques and modes configuration
    """
    from config import STUDY_TECHNIQUES, STUDY_MODES, USER_STATES
    
    return {
        "techniques": STUDY_TECHNIQUES,
        "modes": STUDY_MODES,
        "user_states": USER_STATES,
        "cv_pipeline": "Three-model pipeline (Face + Eye + Emotion)",
        "ml_features": {
            "enabled_when_camera_on": [
                "Face Detection (TFLite)",
                "Eye Tracking (MediaPipe)",
                "Emotion Detection (Keras)"
            ],
            "note": "All CV features automatically enabled when camera is turned on"
        }
    }


# ML service status endpoint
@app.get("/api/ml-status")
async def get_ml_status():
    """
    Get ML service status
    Returns current status of the three-model vision pipeline
    """
    try:
        from services.vision_pipeline import vision_pipeline
        return vision_pipeline.get_pipeline_status()
    except Exception as e:
        logger.error(f"Error getting ML status: {e}")
        return {
            "pipeline_ready": False,
            "error": str(e),
            "message": "Failed to get pipeline status"
        }


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for unhandled errors"""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "detail": "An unexpected error occurred",
            "error": str(exc) if settings.DEBUG else "Internal server error"
        }
    )


# 404 handler
@app.exception_handler(404)
async def not_found_handler(request, exc):
    """Custom 404 handler"""
    return JSONResponse(
        status_code=404,
        content={
            "detail": "Endpoint not found",
            "path": str(request.url.path)
        }
    )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info"
    )
