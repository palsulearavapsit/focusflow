"""
FocusFlow Authentication Routes - Supabase Edition
Refactored to use Supabase Auth SDK
"""

from fastapi import APIRouter, HTTPException, status, Depends
from schemas import (
    UserSignupRequest,
    UserLoginRequest,
    TokenResponse,
    UserBaseResponse
)
from database import db as supabase_db, get_user_by_id
from auth import get_current_user
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def signup(user_data: UserSignupRequest):
    """
    Register a new account via Supabase Auth
    """
    try:
        # Sign up with Supabase
        response = supabase_db.client.auth.sign_up({
            "email": user_data.email,
            "password": user_data.password,
            "options": {
                "data": {
                    "username": user_data.username,
                    "role": user_data.role
                }
            }
        })
        
        if not response.session:
            # If email verification is enabled, session won't be returned immediately
            return TokenResponse(
                access_token="verification_required",
                token_type="bearer",
                user=UserBaseResponse(id="pending", username=user_data.username, email=user_data.email, role=user_data.role)
            )

        # Get the profile that was auto-created by the SQL trigger
        profile = get_user_by_id(response.user.id)
        
        return TokenResponse(
            access_token=response.session.access_token,
            token_type="bearer",
            user=profile or response.user
        )
        
    except Exception as e:
        logger.error(f"❌ Supabase signup error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/login", response_model=TokenResponse)
async def login(credentials: UserLoginRequest):
    """
    Login via Supabase Auth
    """
    try:
        response = supabase_db.client.auth.sign_in_with_password({
            "email": credentials.email,
            "password": credentials.password
        })
        
        # Fetch detailed profile
        profile = get_user_by_id(response.user.id)
        
        return TokenResponse(
            access_token=response.session.access_token,
            token_type="bearer",
            user=profile
        )
        
    except Exception as e:
        logger.error(f"❌ Supabase login error for {credentials.email}: {e}")
        # Log if client is None
        if not supabase_db.client:
            logger.error("⚠️ Supabase client is NOT initialized. Check SUPABASE_URL and SUPABASE_KEY secrets.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Login failed: {str(e)}" if settings.DEBUG else "Incorrect email or password"
        )

@router.get("/verify")
async def verify_token(current_user: dict = Depends(get_current_user)):
    """
    Verify token and return profile
    """
    return current_user
