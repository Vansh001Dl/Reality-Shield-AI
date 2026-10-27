"""Custom exception handling for RealityShield-AI."""

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError
import logging
import time
import uuid
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class CustomExceptionHandler:
    """Handles various types of exceptions with consistent error responses."""

    @staticmethod
    def validation_exception_handler(request: Request, exc: PydanticValidationError):
        """Handle Pydantic validation errors."""
        error_id = str(uuid.uuid4())
        error_details = []

        for error in exc.errors():
            error_details.append({
                "field": " -> ".join(str(loc) for loc in error["loc"]),
                "message": error["msg"],
                "type": error["type"],
                "input": error.get("input")
            })

        logger.warning(
            f"Validation error [ID: {error_id}] | "
            f"URL: {request.url} | "
            f"Method: {request.method} | "
            f"Details: {error_details}"
        )

        return JSONResponse(
            status_code=422,
            content={
                "error": "Validation Error",
                "message": "Request payload validation failed",
                "error_id": error_id,
                "details": error_details,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "path": str(request.url.path),
                "method": request.method
            }
        )

    @staticmethod
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Handle HTTP exceptions with logging."""
        error_id = str(uuid.uuid4())
        logger.warning(
            f"HTTP Exception [ID: {error_id}] | "
            f"Status: {exc.status_code} | "
            f"URL: {request.url} | "
            f"Method: {request.method} | "
            f"Detail: {exc.detail}"
        )

        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.detail,
                "message": "Request failed",
                "error_id": error_id,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "path": str(request.url.path),
                "method": request.method,
                "request_id": request.headers.get("X-Request-ID")
            }
        )

    @staticmethod
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle all other exceptions."""
        error_id = str(uuid.uuid4())
        logger.error(
            f"Internal Server Error [ID: {error_id}] | "
            f"URL: {request.url} | "
            f"Method: {request.method} | "
            f"Exception: {type(exc).__name__}: {str(exc)}",
            exc_info=True
        )

        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal Server Error",
                "message": "An unexpected error occurred",
                "error_id": error_id,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "path": str(request.url.path),
                "method": request.method,
                "request_id": request.headers.get("X-Request-ID"),
                "support_id": f"ERR_{int(time.time())}"
            }
        )


def register_exception_handlers(app):
    """Register all custom exception handlers with the FastAPI app."""
    app.add_exception_handler(PydanticValidationError, CustomExceptionHandler.validation_exception_handler)
    app.add_exception_handler(HTTPException, CustomExceptionHandler.http_exception_handler)
    app.add_exception_handler(Exception, CustomExceptionHandler.general_exception_handler)

    logger.info("Custom exception handlers registered")


# Custom exception classes
class RealityShieldException(Exception):
    """Base exception for RealityShield-AI."""

    def __init__(self, message: str, status_code: int = 500, details: Dict[str, Any] = None):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class AuthenticationError(RealityShieldException):
    """Authentication related errors."""

    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, status_code=401)


class AuthorizationError(RealityShieldException):
    """Authorization related errors."""

    def __init__(self, message: str = "Access denied"):
        super().__init__(message, status_code=403)


class ResourceNotFoundError(RealityShieldException):
    """Resource not found errors."""

    def __init__(self, resource: str = "Resource", identifier: str = ""):
        message = f"{resource} not found"
        if identifier:
            message += f": {identifier}"
        super().__init__(message, status_code=404)


class ValidationError(RealityShieldException):
    """Custom validation errors."""

    def __init__(self, message: str = "Validation failed", details: Dict[str, Any] = None):
        super().__init__(message, status_code=422, details=details)


class BusinessLogicError(RealityShieldException):
    """Business logic errors."""

    def __init__(self, message: str = "Business logic error"):
        super().__init__(message, status_code=400)


class ExternalServiceError(RealityShieldException):
    """External service errors."""

    def __init__(self, service: str = "External service", message: str = "Service unavailable"):
        super().__init__(f"{service}: {message}", status_code=503)


class RateLimitError(RealityShieldException):
    """Rate limit exceeded errors."""

    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(message, status_code=429)