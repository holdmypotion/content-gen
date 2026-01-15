import logging
from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional

from db import get_db
from utils.auth import create_access_token, verify_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


class SignupRequest(BaseModel):
    email: EmailStr
    username: str
    password: str
    
    @field_validator('username')
    def validate_username(cls, v):
        if len(v) < 3:
            raise ValueError('Username must be at least 3 characters')
        if not v.isalnum():
            raise ValueError('Username must be alphanumeric')
        return v
    
    @field_validator('password')
    def validate_password(cls, v):
        if len(v) < 6:
            raise ValueError('Password must be at least 6 characters')
        if len(v) > 72:
            raise ValueError('Password must be at most 72 characters')
        return v


class LoginRequest(BaseModel):
    email_or_username: str
    password: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class UserResponse(BaseModel):
    id: str
    email: str
    username: str


@router.post("/signup", response_model=AuthResponse)
async def signup(request: SignupRequest):
    """Create a new user account."""
    try:
        db = get_db()
        user_id = db.users.create_user(
            email=request.email,
            username=request.username,
            password=request.password
        )
        
        token = create_access_token(user_id)
        user = db.users.get_user(user_id)
        
        return {
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "id": user["_id"],
                "email": user["email"],
                "username": user["username"]
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Signup error: {str(e)}")
        raise HTTPException(status_code=500, detail="Signup failed")


@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest):
    """Login with email or username."""
    try:
        db = get_db()
        user_id = db.users.verify_user(request.email_or_username, request.password)
        
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        token = create_access_token(user_id)
        user = db.users.get_user(user_id)
        
        return {
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "id": user["_id"],
                "email": user["email"],
                "username": user["username"]
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(status_code=500, detail="Login failed")


@router.post("/verify")
async def verify(authorization: Optional[str] = Header(None)):
    """Verify a token and return user info."""
    try:
        if not authorization:
            raise HTTPException(status_code=401, detail="Missing authorization header")
        
        # Extract token from "Bearer <token>"
        try:
            scheme, token = authorization.split()
            if scheme.lower() != "bearer":
                raise ValueError("Invalid authorization scheme")
        except ValueError:
            raise HTTPException(status_code=401, detail="Invalid authorization header format")
        
        user_id = verify_token(token)
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        
        db = get_db()
        user = db.users.get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {
            "id": user["_id"],
            "email": user["email"],
            "username": user["username"]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token verification error: {str(e)}")
        raise HTTPException(status_code=500, detail="Token verification failed")
