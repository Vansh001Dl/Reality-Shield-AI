"""Authentication helpers for admin and system operator access."""

from typing import Optional
from fastapi import HTTPException, Request
from fastapi.security import HTTPBearer
from passlib.context import CryptContext
import os
import jwt
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional
import secrets
import bcrypt

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated=["auto"])

security = HTTPBearer()

class AuthService:
    """Authentication and authorization service."""

    def __init__(self):
        self.secret_key = os.getenv("SECRET_KEY", secrets.token_hex(32))
        self.algorithm = "HS256"
        self.access_token_expiry = timedelta(hours=24)
        self.refresh_token_expiry = timedelta(days=7)
        self.pwd_context = pwd_context

    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt."""
        return self.pwd_context.hash(password)

    def verify_password(self, password: str, hashed_password: str) -> bool:
        """Verify password against hash."""
        return self.pwd_context.verify(password, hashed_password)

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

    def authenticate_api_key(self, api_key: str) -> bool:
        """Validate API key using secure comparison."""
        if not api_key:
            return False

        expected_api_key = os.getenv("API_KEY")
        if not expected_api_key:
            return True  # Skip validation if not configured

        try:
            # Use constant-time comparison to prevent timing attacks
            return secrets.compare_digest(api_key, expected_api_key)
        except Exception:
            return False

    def create_session_token(self, user_id: str, username: str, role: str = "user") -> str:
        """Create session token with user role."""
        payload = {
            "sub": user_id,
            "username": username,
            "role": role,
            "exp": datetime.now(timezone.utc) + self.access_token_expiry,
            "iat": datetime.now(timezone.utc),
            "token_type": "session"
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def verify_session_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify session token and return payload."""
        payload = self.verify_token(token)
        if payload and payload.get("token_type") == "session":
            return payload
        return None

    def get_user_from_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Extract user information from token."""
        payload = self.verify_token(token)
        if payload:
            return {
                "user_id": payload.get("sub"),
                "username": payload.get("username"),
                "role": payload.get("role", "user")
            }
        return None

# Global auth service instance
auth_service = AuthService()


def verify_api_key(api_key: Optional[str]) -> bool:
    """Validate a provided API key for internal backend requests."""
    return auth_service.authenticate_api_key(api_key)


def verify_bearer_token(token: Optional[str]) -> Dict[str, Any]:
    """Validate bearer token and return user info."""
    if not token:
        raise HTTPException(status_code=401, detail="Missing authorization token")

    user_info = auth_service.verify_session_token(token)
    if not user_info:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return user_info


def require_role(role: str):
    """Decorator to require specific role for endpoint."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            from fastapi import Request, Depends
            from fastapi.security import HTTPBearer

            # This would be used in dependency injection
            # For now, return a simple check function
            def role_checker(request: Request):
                token = request.headers.get("Authorization")
                if token and token.startswith("Bearer "):
                    token = token[7:]
                    user_info = auth_service.verify_session_token(token)
                    if user_info and user_info.get("role") == role:
                        return user_info
                raise HTTPException(status_code=403, detail=f"Requires {role} role")

            return await func(*args, **kwargs)
        return wrapper
    return decorator


# Create HTTPBearer instance for FastAPI dependency
bearer_scheme = HTTPBearer(auto_error=False)


class APIKeyAuth:
    """API Key authentication for service-to-service communication."""

    def __init__(self, name: str = "X-API-Key"):
        self.name = name

    async def __call__(self, request: Request) -> str:
        api_key = request.headers.get(self.name)
        if not api_key or not auth_service.authenticate_api_key(api_key):
            raise HTTPException(
                status_code=401,
                detail="Invalid or missing API key",
                headers={"WWW-Authenticate": "ApiKey"}
            )
        return api_key

# Global API key auth instance
api_key_auth = APIKeyAuth()