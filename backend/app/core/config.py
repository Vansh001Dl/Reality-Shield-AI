"""Application settings and environment configuration for RealityShield-AI."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List
import os
import secrets

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[3] / ".env")


def _default_database_url() -> str:
    postgres_url = "postgresql+psycopg2://postgres:postgres@localhost:5432/realityshield"
    if os.getenv("APP_ENV", "development").lower() == "production":
        return postgres_url

    database_path = Path(__file__).resolve().parents[2] / "data" / "users.sqlite3"
    return f"sqlite:///{database_path.as_posix()}"


@dataclass
class Settings:
    """Container for backend configuration values."""
    app_name: str = "RealityShield-AI"
    debug: bool = False
    api_prefix: str = "/api"
    database_url: str = os.getenv("DATABASE_URL", _default_database_url())
    celery_enabled: bool = os.getenv("CELERY_ENABLED", "false").lower() == "true"
    frontend_url: str = os.getenv("FRONTEND_URL", "http://localhost:3000")

    # Security
    secret_key: str = os.getenv("SECRET_KEY", secrets.token_hex(32))
    api_key: str = os.getenv("API_KEY", secrets.token_hex(16))
    cors_origins: List[str] = field(default_factory=lambda: os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173").split(","))

    # AI Configuration
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    roboflow_api_key: str = os.getenv("ROBOFLOW_API_KEY", "")
    roboflow_model_id: str = os.getenv("ROBOFLOW_MODEL_ID", "")
    roboflow_api_url: str = os.getenv("ROBOFLOW_API_URL", "https://detect.roboflow.com")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
    groq_model: str = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
    yolo_model_path: str = os.getenv("YOLO_MODEL_PATH", "./ml_models/yolo_weights/best.pt")
    risk_model_path: str = os.getenv("RISK_MODEL_PATH", "./ml_models/risk_model.pkl")
    default_yolo_weights: str = os.getenv("DEFAULT_YOLO_WEIGHTS", "yolov8n.pt")

    # Cloud Storage
    aws_access_key_id: str = os.getenv("AWS_ACCESS_KEY_ID", "")
    aws_secret_access_key: str = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    aws_session_token: str = os.getenv("AWS_SESSION_TOKEN", "")
    aws_region: str = os.getenv("AWS_REGION", "us-east-1")
    s3_bucket_name: str = os.getenv("S3_BUCKET_NAME", "realityshield-videos")
    s3_dataset_storage_prefix: str = os.getenv("S3_DATASET_STORAGE_PREFIX", "datasets")

    # Rate Limiting
    rate_limit: int = int(os.getenv("RATE_LIMIT", "1000"))
    rate_limit_window: int = int(os.getenv("RATE_LIMIT_WINDOW", "60"))
    session_timeout: int = int(os.getenv("SESSION_TIMEOUT", "3600"))

    # Logging
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    log_file: str = os.getenv("LOG_FILE", "logs/app.log")
    error_log_file: str = os.getenv("ERROR_LOG_FILE", "logs/error.log")

    # Upload settings
    max_file_size_mb: int = int(os.getenv("MAX_FILE_SIZE_MB", "100"))
    allowed_file_extensions: List[str] = field(default_factory=lambda: [".mp4", ".avi", ".mov", ".mkv", ".webm", ".jpg", ".jpeg", ".png", ".bmp"])

    # Environment
    environment: str = os.getenv("APP_ENV", "development")
    port: int = int(os.getenv("PORT", "8000"))
    host: str = os.getenv("HOST", "0.0.0.0")

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        return self.environment == "development"

    def validate(self) -> List[str]:
        """Validate configuration and return list of issues"""
        issues = []
        if self.is_production:
            if self.secret_key == secrets.token_hex(32):
                issues.append("SECRET_KEY not set for production")
            if self.database_url == "postgresql+psycopg2://postgres:postgres@localhost:5432/realityshield":
                issues.append("DATABASE_URL not configured for production")
            if not self.groq_api_key and not self.gemini_api_key:
                issues.append("No LLM API key configured")
        return issues

settings = Settings()
