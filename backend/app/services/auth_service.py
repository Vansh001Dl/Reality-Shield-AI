"""Authentication service for RealityShield-AI."""

import os
import jwt
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional
from fastapi import HTTPException
from pydantic import BaseModel, EmailStr, Field
import secrets
import uuid

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.core.security import pwd_context

class UserCreate(BaseModel):
    """User creation model."""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: Optional[str] = None

class UserLogin(BaseModel):
    """User login model."""
    username: str
    password: str

class TokenResponse(BaseModel):
    """Token response model."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user_id: str

class UserResponse(BaseModel):
    """User response model."""
    id: str
    username: str
    email: str
    full_name: Optional[str] = None
    is_active: bool = True
    is_verified: bool = False
    created_at: datetime

class UserService:
    """User authentication and management service."""

    def __init__(self):
        self.secret_key = os.getenv("SECRET_KEY", secrets.token_hex(32))
        self.algorithm = "HS256"
        self.access_token_expiry = timedelta(hours=24)
        self.refresh_token_expiry = timedelta(days=7)

    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt."""
        return pwd_context.hash(password)

    def verify_password(self, password: str, hashed_password: str) -> bool:
        """Verify password against hash."""
        return pwd_context.verify(password, hashed_password)

    def create_access_token(self, user_id: str, username: str) -> str:
        """Create JWT access token."""
        payload = {
            "sub": user_id,
            "username": username,
            "exp": datetime.now(timezone.utc) + self.access_token_expiry,
            "iat": datetime.now(timezone.utc),
            "token_type": "access"
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def create_refresh_token(self, user_id: str) -> str:
        """Create JWT refresh token."""
        payload = {
            "sub": user_id,
            "exp": datetime.now(timezone.utc) + self.refresh_token_expiry,
            "iat": datetime.now(timezone.utc),
            "token_type": "refresh"
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify and decode JWT token."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token has expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")

    def authenticate_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate user credentials."""
        admin_username = os.getenv("ADMIN_USERNAME", "admin")
        admin_password = os.getenv("ADMIN_PASSWORD", "admin123")
        admin_email = os.getenv("ADMIN_EMAIL", "admin@realityshield.ai")

        if username == admin_username and password == admin_password:
            return {
                "id": "admin_001",
                "username": username,
                "email": admin_email,
                "full_name": "System Administrator",
                "is_active": True,
                "is_verified": True,
                "role": "admin"
            }

        user = self.get_user_by_username(username)
        if not user or not user["is_active"] or not self.verify_password(password, user["hashed_password"]):
            return None
        return user

    def create_user(self, user_data: UserCreate) -> Optional[Dict[str, Any]]:
        """Create a new user."""
        user = {
            "id": str(uuid.uuid4()),
            "username": user_data.username,
            "email": user_data.email,
            "full_name": user_data.full_name,
            "hashed_password": self.hash_password(user_data.password),
            "is_active": True,
            "is_verified": False,
            "created_at": datetime.now(timezone.utc),
            "role": "viewer"
        }

        from app.db.database import get_db_context
        try:
            with get_db_context() as db:
                db.execute(
                    text(
                        """
                        INSERT INTO users
                            (id, username, email, full_name, hashed_password, is_active, is_verified, created_at, role)
                        VALUES
                            (:id, :username, :email, :full_name, :hashed_password, :is_active, :is_verified, :created_at, :role)
                        """
                    ),
                    user,
                )
        except IntegrityError:
            return None
        return user

    def user_exists(self, username: str, email: str) -> bool:
        """Check if user exists."""
        from app.db.database import get_db_context
        with get_db_context() as db:
            row = db.execute(
                text("SELECT 1 FROM users WHERE username = :username OR email = :email LIMIT 1"),
                {"username": username, "email": email},
            ).first()
        return row is not None

    def save_user(self, user: Dict[str, Any]) -> bool:
        """Save user to database."""
        from app.db.database import get_db_context
        with get_db_context() as db:
            db.execute(
                text(
                    """
                    INSERT INTO users
                        (id, username, email, full_name, hashed_password, is_active, is_verified, created_at, role)
                    VALUES
                        (:id, :username, :email, :full_name, :hashed_password, :is_active, :is_verified, :created_at, :role)
                    """
                ),
                user,
            )
        return True

    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID."""
        from app.db.database import get_db_context
        with get_db_context() as db:
            row = db.execute(
                text("SELECT * FROM users WHERE id = :user_id"),
                {"user_id": user_id},
            ).mappings().first()
        return dict(row) if row else None

    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user by username."""
        from app.db.database import get_db_context
        with get_db_context() as db:
            row = db.execute(
                text("SELECT * FROM users WHERE username = :username"),
                {"username": username},
            ).mappings().first()
        return dict(row) if row else None

    def update_user(self, user_id: str, user_data: Dict[str, Any]) -> bool:
        """Update user information."""
        allowed_fields = {"username", "email", "full_name", "is_active", "is_verified", "role"}
        updates = {key: value for key, value in user_data.items() if key in allowed_fields}
        if not updates:
            return False
        assignments = ", ".join(f"{key} = :{key}" for key in updates)
        from app.db.database import get_db_context
        with get_db_context() as db:
            result = db.execute(
                text(f"UPDATE users SET {assignments} WHERE id = :user_id"),
                {**updates, "user_id": user_id},
            )
        return result.rowcount > 0

    def delete_user(self, user_id: str) -> bool:
        """Delete user."""
        from app.db.database import get_db_context
        with get_db_context() as db:
            result = db.execute(
                text("DELETE FROM users WHERE id = :user_id"),
                {"user_id": user_id},
            )
        return result.rowcount > 0

    def list_users(self) -> list:
        """List all users."""
        from app.db.database import get_db_context
        with get_db_context() as db:
            rows = db.execute(text("SELECT * FROM users ORDER BY created_at DESC")).mappings().all()
        return [dict(row) for row in rows]

    def verify_session_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify an access token and return its corresponding user."""
        payload = self.verify_token(token)
        if payload.get("token_type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user_id = payload.get("sub")
        if user_id == "admin_001":
            return {
                "id": user_id,
                "username": payload.get("username", os.getenv("ADMIN_USERNAME", "admin")),
                "email": os.getenv("ADMIN_EMAIL", "admin@realityshield.ai"),
                "role": "admin",
            }
        user = self.get_user_by_id(user_id) if user_id else None
        if not user or not user["is_active"]:
            return None
        return {
            key: user[key]
            for key in ("id", "username", "email", "full_name", "is_active", "is_verified", "created_at", "role")
        }

# Global service instance
auth_service = UserService()