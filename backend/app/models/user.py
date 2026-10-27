"""User and authentication models for RealityShield-AI."""

from datetime import datetime, timezone
from typing import Optional, List
from pydantic import BaseModel, Field, EmailStr, validator
import uuid

class UserBase(BaseModel):
    """Base user model."""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    full_name: Optional[str] = None
    is_active: bool = True
    is_verified: bool = False

class UserCreate(UserBase):
    """User creation model."""
    password: str = Field(..., min_length=8, max_length=128)

    @validator('password')
    def password_strength(cls, v):
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        return v

class UserUpdate(BaseModel):
    """User update model."""
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None
    password: Optional[str] = Field(None, min_length=8)

class UserLogin(BaseModel):
    """User login model."""
    username: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=1, max_length=128)

class UserInDB(UserBase):
    """User model stored in database."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    hashed_password: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_login: Optional[datetime] = None
    failed_login_attempts: int = 0
    locked_until: Optional[datetime] = None

class UserResponse(UserBase):
    """User response model (excludes sensitive fields)."""
    id: str
    created_at: datetime
    last_login: Optional[datetime] = None

class TokenData(BaseModel):
    """Token payload data."""
    sub: Optional[str] = None
    username: Optional[str] = None
    exp: Optional[int] = None
    token_type: Optional[str] = None

class TokenResponse(BaseModel):
    """Token response model."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user_id: str

class RoleEnum(str):
    ADMIN = "admin"
    OPERATOR = "operator"
    VIEWER = "viewer"

class UserRole(BaseModel):
    """User role model."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    role: str = Field(default="viewer")
    permissions: List[str] = Field(default_factory=list)
    granted_by: Optional[str] = None
    granted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))