"""FastAPI entry point for the RealityShield-AI backend service."""

from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager
from typing import Any, Dict

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from starlette.responses import Response
from app.core.middleware import RateLimitMiddleware
from app.core.metrics import CONTENT_TYPE_LATEST, REQUEST_COUNT, REQUEST_LATENCY, generate_latest
from app.core.realtime import router as realtime_router

from app.api.routes_alerts import router as alerts_router
from app.api.routes_analytics import router as analytics_router
from app.api.routes_auth import router as auth_router
from app.api.routes_chat import router as chat_router
from app.api.routes_detection import router as detection_router
from app.api.routes_explain import router as explain_router
from app.api.routes_risk import router as risk_router
from app.api.routes_route import router as route_router
from app.api.routes_weather import router as weather_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import RequestLogger, configure_logging
from app.core.security import api_key_auth

# Configure logging first
configure_logging()
logger = logging.getLogger(__name__)


def _build_health_status() -> Dict[str, Any]:
    """Collect backend readiness signals without crashing the service."""
    status: Dict[str, Any] = {
        "status": "healthy",
        "service": "RealityShield-AI",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "version": "0.1.0",
        "environment": settings.environment,
    }

    try:
        from sqlalchemy import text
        from app.db.database import get_db_context

        with get_db_context() as db:
            db.execute(text("SELECT 1"))
        status["database"] = {"status": "connected", "provider": "sqlalchemy"}
    except Exception as exc:
        status["database"] = {"status": "disconnected", "error": str(exc)}
        status["status"] = "degraded"

    try:
        from app.services.vision_agent import load_yolo_model

        load_yolo_model()
        status["model"] = {"status": "loaded", "kind": "yolo"}
    except Exception as exc:
        status["model"] = {"status": "unavailable", "error": str(exc)}
        status["status"] = "degraded"

    return status


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    logger.info("Starting RealityShield-AI application...")
    logger.info("Environment: %s", settings.environment)
    logger.info("Database provider configured")

    issues = settings.validate()
    if issues:
        for issue in issues:
            logger.warning("Configuration issue: %s", issue)

    try:
        from app.db.database import init_db

        init_db()
        logger.info("Database initialized successfully")
    except Exception as exc:
        logger.error("Database initialization failed: %s", exc)

    try:
        from app.services.vision_agent import load_yolo_model

        load_yolo_model()
        logger.info("ML model loaded successfully")
    except Exception as exc:
        logger.warning("ML model loading failed: %s", exc)

    yield
    logger.info("Shutting down RealityShield-AI application...")


app = FastAPI(
    title="RealityShield-AI",
    version="0.1.0",
    docs_url="/api/docs" if settings.environment != "production" else None,
    redoc_url="/api/redoc" if settings.environment != "production" else None,
    lifespan=lifespan,
)

app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(RateLimitMiddleware, requests_per_window=settings.rate_limit, window_seconds=settings.rate_limit_window)
app.add_middleware(RequestLogger)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=(
        r"^https?://(?:localhost|127\.0\.0\.1)(?::\d+)?$"
        if settings.is_development
        else None
    ),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Total-Count", "X-RateLimit-Remaining", "X-Request-ID"],
)

register_exception_handlers(app)


@app.get("/health", tags=["health"])
@app.get("/api/health", tags=["health"])
@app.get("/api/v1/health", tags=["health"])
async def health_check() -> Dict[str, Any]:
    """Comprehensive health check for deployment, monitoring, and frontend compatibility."""
    return _build_health_status()


@app.get("/ready", tags=["health"])
@app.get("/api/ready", tags=["health"])
@app.get("/api/v1/ready", tags=["health"])
async def readiness_check() -> Dict[str, Any]:
    """Readiness endpoint for load balancers and startup verification."""
    status = _build_health_status()
    ready = status["database"].get("status") == "connected" and status["model"].get("status") == "loaded"
    return {
        "status": "ready" if ready else "degraded",
        "ready": ready,
        "checks": {
            "database": status["database"],
            "model": status["model"],
        },
        "timestamp": status["timestamp"],
    }


@app.get("/api/auth/verify", tags=["auth"])
@app.get("/api/v1/auth/verify", tags=["auth"])
async def verify_api_key_endpoint(request: Request, api_key: str | None = None):
    """Verify API key validity for compatibility with the frontend and service integrations."""
    if not api_key:
        api_key = request.headers.get("X-API-Key")

    if not api_key:
        raise HTTPException(status_code=401, detail="Missing API key")

    is_valid = api_key_auth.authenticate_api_key(api_key)
    return {
        "valid": is_valid,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


for api_router in (auth_router, alerts_router, analytics_router, chat_router, detection_router, explain_router, risk_router, route_router, weather_router):
    app.include_router(api_router, prefix="/api/v1")
    app.include_router(api_router, prefix="/api", include_in_schema=False)

@app.get("/metrics", include_in_schema=False)
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.get("/api/v1/metrics", include_in_schema=False)
async def versioned_metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.middleware("http")
async def collect_metrics(request: Request, call_next):
    started = time.perf_counter()
    response = await call_next(request)
    if request.url.path not in {"/metrics", "/api/v1/metrics"}:
        route = request.scope.get("route")
        path = getattr(route, "path", request.url.path)
        REQUEST_COUNT.labels(request.method, path, str(response.status_code)).inc()
        REQUEST_LATENCY.labels(request.method, path).observe(time.perf_counter() - started)
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch-all error handler for unhandled exceptions."""
    logger.error("Unhandled exception: %s", exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "request_id": request.headers.get("X-Request-ID", "unknown"),
        },
    )


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests."""
    request_id = f"req_{int(time.time() * 1000)}"
    start_time = time.time()
    logger.info("Request: %s %s", request.method, request.url)

    response = await call_next(request)

    duration = (time.time() - start_time) * 1000
    logger.info("Response: %s %s - %s - %.2fms", request.method, request.url, response.status_code, duration)

    response.headers["X-Request-ID"] = request_id
    return response
