"""
FocusFlow Authentication Module
JWT token generation and validation
"""

from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from config import settings
from database import get_user_by_email, get_user_by_id
import logging

logger = logging.getLogger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# HTTP Bearer token scheme
security = HTTPBearer()


def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token
    
    Args:
        data: Dictionary containing user data to encode
        expires_delta: Optional token expiration time
    
    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=settings.ACCESS_TOKEN_EXPIRE_HOURS)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow()
    })
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    
    return encoded_jwt


def decode_access_token(token: str) -> dict:
    """
    Decode and validate a JWT token
    
    Args:
        token: JWT token string
    
    Returns:
        Decoded token payload
    
    Raises:
        HTTPException: If token is invalid or expired
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError as e:
        logger.error(f"JWT decode error: {e}")
        raise credentials_exception


def authenticate_user(email: str, password: str) -> Optional[dict]:
    """
    Authenticate a user with email and password
    
    Args:
        email: User email
        password: Plain text password
    
    Returns:
        User dict if authenticated, None otherwise
    """
    user = get_user_by_email(email)
    
    if not user:
        return None
    
    if not verify_password(password, user['password_hash']):
        return None
    
    return user


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """
    Get current authenticated user from JWT token
    
    Args:
        credentials: HTTP Bearer credentials
    
    Returns:
        Current user dict
    
    Raises:
        HTTPException: If authentication fails
    """
    token = credentials.credentials
    payload = decode_access_token(token)
    
    user_id: int = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )
    
    user = get_user_by_id(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    return user


async def get_current_student(current_user: dict = Depends(get_current_user)) -> dict:
    """
    Verify current user is a student
    
    Args:
        current_user: Current authenticated user
    
    Returns:
        Current user dict if role is student
    
    Raises:
        HTTPException: If user is not a student
    """
    if current_user['role'] != 'student':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: Student role required"
        )
    return current_user


async def get_current_admin(current_user: dict = Depends(get_current_user)) -> dict:
    """
    Verify current user is an admin
    
    Args:
        current_user: Current authenticated user
    
    Returns:
        Current user dict if role is admin
    
    Raises:
        HTTPException: If user is not an admin
    """
    if current_user['role'] != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: Admin role required"
        )
    return current_user


async def get_current_teacher(current_user: dict = Depends(get_current_user)) -> dict:
    """
    Verify current user is a teacher
    """
    if current_user['role'] != 'teacher':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: Teacher role required"
        )
    return current_user


def create_user_token(user: dict) -> str:
    """
    Create JWT token for a user
    
    Args:
        user: User dictionary from database
    
    Returns:
        JWT token string
    """
    token_data = {
        "sub": str(user['id']),
        "email": user['email'],
        "role": user['role'],
        "username": user['username']
    }
    
    return create_access_token(token_data)
