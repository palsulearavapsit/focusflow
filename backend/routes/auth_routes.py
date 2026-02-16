"""
FocusFlow Authentication Routes
Handles user signup and login endpoints
"""

from fastapi import APIRouter, HTTPException, status, Depends
from schemas import (
    UserSignupRequest,
    UserLoginRequest,
    TokenResponse,
    UserResponse
)
from auth import authenticate_user, create_user_token, hash_password, get_current_user
from database import get_user_by_email, create_user
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def signup(user_data: UserSignupRequest):
    """
    Register a new student account
    
    - **username**: Unique username (3-50 characters, alphanumeric)
    - **email**: Valid email address
    - **password**: Password (minimum 6 characters)
    
    Returns JWT token and user information
    """
    try:
        # Check if email already exists
        existing_user = get_user_by_email(user_data.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Hash password
        password_hash = hash_password(user_data.password)
        
        # Create user
        user_id = create_user(
            username=user_data.username,
            email=user_data.email,
            password_hash=password_hash,
            role=user_data.role
        )
        
        # Get created user
        user = get_user_by_email(user_data.email)
        
        # Create JWT token
        token = create_user_token(user)
        
        logger.info(f"✅ New user registered: {user_data.email}")
        
        return TokenResponse(
            access_token=token,
            token_type="bearer",
            user=UserResponse(**user)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Signup error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed. Please try again."
        )


@router.post("/login", response_model=TokenResponse)
async def login(credentials: UserLoginRequest):
    """
    Login with email and password
    
    - **email**: Registered email address
    - **password**: User password
    
    Returns JWT token and user information
    
    **Admin Login:**
    - Email: admin@focusflow.com
    - Password: admin123
    """
    try:
        # Authenticate user
        user = authenticate_user(credentials.email, credentials.password)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Create JWT token
        token = create_user_token(user)
        
        logger.info(f"✅ User logged in: {credentials.email} (Role: {user['role']})")
        
        return TokenResponse(
            access_token=token,
            token_type="bearer",
            user=UserResponse(**user)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed. Please try again."
        )


@router.get("/verify", response_model=UserResponse)
async def verify_token(current_user: dict = Depends(get_current_user)):
    """
    Verify JWT token and get current user
    
    Requires valid JWT token in Authorization header
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    return UserResponse(**current_user)
