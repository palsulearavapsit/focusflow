"""
FocusFlow Authentication Routes - MySQL Edition
JWT-based signup / login / verify
"""

from fastapi import APIRouter, HTTPException, status, Depends
from schemas import (
    UserSignupRequest,
    UserLoginRequest,
    TokenResponse,
    UserBaseResponse,
    UserResponse
)
from database import get_user_by_email, create_user
from auth import verify_password, hash_password, create_access_token, get_current_user
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def signup(user_data: UserSignupRequest):
    """Register a new user account"""
    # Check existing email
    if get_user_by_email(user_data.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    try:
        hashed = hash_password(user_data.password)
        user = create_user(user_data.username, user_data.email, hashed, user_data.role.value)

        token = create_access_token({"sub": str(user["id"])})

        return TokenResponse(
            access_token=token,
            token_type="bearer",
            user=UserBaseResponse(
                id=str(user["id"]),
                username=user["username"],
                email=user["email"],
                role=user["role"]
            )
        )
    except Exception as e:
        logger.error(f"❌ Signup error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/login", response_model=TokenResponse)
async def login(credentials: UserLoginRequest):
    """Login with email and password"""
    user = get_user_by_email(credentials.email)

    if not user or not verify_password(credentials.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    token = create_access_token({"sub": str(user["id"])})

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserBaseResponse(
            id=str(user["id"]),
            username=user["username"],
            email=user["email"],
            role=user["role"]
        )
    )


@router.get("/verify")
async def verify_token(current_user: dict = Depends(get_current_user)):
    """Verify token and return current user profile"""
    # Convert id to string for frontend
    current_user["id"] = str(current_user["id"])
    return current_user
