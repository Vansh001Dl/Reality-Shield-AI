"""Authentication endpoints for RealityShield-AI."""

from datetime import datetime, timezone
import os
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer
from typing import Dict, Any
from sqlalchemy.exc import SQLAlchemyError

from app.services.auth_service import auth_service, UserCreate, UserLogin, TokenResponse
from app.core.security import bearer_scheme, verify_bearer_token
from app.core.exceptions import AuthenticationError, ValidationError

router = APIRouter(prefix="/auth", tags=["authentication"])
security = HTTPBearer()

@router.post("/register", status_code=201)
async def register(user_data: UserCreate):
    """Create and persist a user account."""
    try:
        user = auth_service.create_user(user_data)
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503,
            detail="Account storage is unavailable. Start or configure the database and try again.",
        ) from exc

    if not user:
        raise HTTPException(status_code=409, detail="Username or email is already registered.")

    return {
        "success": True,
        "message": "Account created successfully.",
        "user": {
            "id": user["id"],
            "username": user["username"],
            "email": user["email"],
            "full_name": user["full_name"],
        },
    }

@router.post("/login", response_model=TokenResponse)
async def login(user_credentials: UserLogin):
    """User login endpoint with JWT authentication."""
    # Authenticate user credentials
    try:
        user = auth_service.authenticate_user(user_credentials.username, user_credentials.password)
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503,
            detail="Account storage is unavailable. Start or configure the database and try again.",
        ) from exc

    if not user:
        raise AuthenticationError("Invalid username or password")

    # Create JWT tokens
    access_token = auth_service.create_access_token(user["id"], user["username"])
    refresh_token = auth_service.create_refresh_token(user["id"])

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=auth_service.access_token_expiry.total_seconds(),
        user_id=user["id"]
    )

@router.post("/refresh")
async def refresh_token(refresh_token: str):
    """Refresh access token using refresh token."""
    payload = auth_service.verify_token(refresh_token)
    if payload.get("token_type") != "refresh":
        raise AuthenticationError("Invalid token type")

    user_id = payload["sub"]
    if user_id == "admin_001":
        username = os.getenv("ADMIN_USERNAME", "admin")
    else:
        user = auth_service.get_user_by_id(user_id)
        if not user or not user["is_active"]:
            raise AuthenticationError("User account is unavailable")
        username = user["username"]

    access_token = auth_service.create_access_token(user_id, username)
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": auth_service.access_token_expiry.total_seconds()
    }

@router.get("/verify")
async def verify_token(current_user: Dict[str, Any] = Depends(bearer_scheme)):
    """Verify current token and return user info."""
    if not current_user:
        raise AuthenticationError("Invalid or missing token")

    try:
        user_info = auth_service.verify_session_token(current_user.credentials)
        if not user_info:
            raise AuthenticationError("Invalid token")

        return {
            "valid": True,
            "user_info": user_info,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise AuthenticationError(str(e))

@router.post("/logout")
async def logout(current_user: Dict[str, Any] = Depends(bearer_scheme)):
    """Logout user (invalidate token)."""
    # In production, you would add token to blacklist
    return {
        "message": "Logged out successfully",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@router.get("/protected")
async def protected_endpoint(current_user: Dict[str, Any] = Depends(bearer_scheme)):
    """Example protected endpoint requiring authentication."""
    return {
        "message": "This is a protected endpoint",
        "user": current_user,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }