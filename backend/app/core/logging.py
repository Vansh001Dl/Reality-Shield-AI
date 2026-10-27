"""Structured logging configuration for RealityShield-AI."""

import logging
import sys
import os
from datetime import datetime, timezone
from typing import Optional
from pathlib import Path

# Create logs directory
logs_dir = Path("logs")
logs_dir.mkdir(exist_ok=True)

# Custom formatters
class DetailedFormatter(logging.Formatter):
    """Detailed formatter with timestamp, module, and context."""

    def __init__(self):
        super().__init__(
            '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

class JSONFormatter(logging.Formatter):
    """JSON format for structured logging."""

    def __init__(self):
        super().__init__()

    def format(self, record):
        log_record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_record)

# Try importing json
import json

def configure_logging():
    """Configure structured logging for the application."""
    log_level = os.getenv("LOG_LEVEL", "INFO")
    log_file = os.getenv("LOG_FILE", "logs/app.log")
    error_log_file = os.getenv("ERROR_LOG_FILE", "logs/error.log")

    # Ensure log files exist
    Path(log_file).parent.mkdir(parents=True, exist_ok=True)
    Path(error_log_file).parent.mkdir(parents=True, exist_ok=True)

    # Root logger configuration
    root_logger = logging.getLogger()
    level_value = getattr(logging, log_level.upper(), logging.INFO)
    root_logger.setLevel(level_value)

    # Avoid duplicate handlers on repeated app initialization.
    if root_logger.handlers:
        for handler in list(root_logger.handlers):
            if isinstance(handler, logging.StreamHandler) or isinstance(handler, logging.FileHandler):
                root_logger.removeHandler(handler)
                handler.close()

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level_value)
    console_handler.setFormatter(JSONFormatter())
    root_logger.addHandler(console_handler)

    # File handler for general logs
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(JSONFormatter())
    root_logger.addHandler(file_handler)

    # File handler for errors
    error_handler = logging.FileHandler(error_log_file, encoding='utf-8')
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(JSONFormatter())
    root_logger.addHandler(error_handler)

    # Prevent duplicate logs in some configurations
    root_logger.propagate = False

    # Configure module-specific loggers
    module_loggers = {
        "app.api": logging.INFO,
        "app.services": logging.INFO,
        "app.db": logging.INFO,
        "app.core": logging.WARNING,
        "request": logging.INFO,
        "sqlalchemy.engine": logging.WARNING,
        "sqlalchemy.pool": logging.WARNING,
    }

    for logger_name, level in module_loggers.items():
        logger = logging.getLogger(logger_name)
        logger.setLevel(level)
        logger.propagate = True

    # Development-specific configuration
    if os.getenv("APP_ENV") == "development":
        # Enable SQLAlchemy query logging
        sql_logger = logging.getLogger("sqlalchemy.engine")
        sql_logger.setLevel(logging.INFO)
        sql_logger.addHandler(console_handler)

        # Enable request logging
        request_logger = logging.getLogger("request")
        request_logger.setLevel(logging.DEBUG)
        request_logger.addHandler(console_handler)

    return {
        "root_logger": root_logger,
        "log_level": log_level,
        "log_file": log_file,
        "error_log_file": error_log_file
    }


class RequestLogger:
    """Middleware for logging HTTP requests."""

    def __init__(self, app):
        self.app = app
        self.logger = logging.getLogger("request")

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = f"req_{int(datetime.now(timezone.utc).timestamp() * 1000)}"
        method = scope["method"]
        path = scope["path"]
        client_ip = scope.get("client", [None, None])[0]

        start_time = datetime.now(timezone.utc)

        self.logger.info(
            f"Request started | ID: {request_id} | "
            f"{method} {path} | IP: {client_ip}"
        )

        # Capture response status
        original_send = send

        async def custom_send(message):
            if message["type"] == "http.response.start":
                status_code = message.get("status")
                end_time = datetime.now(timezone.utc)
                duration = (end_time - start_time).total_seconds() * 1000

                self.logger.info(
                    f"Request completed | ID: {request_id} | "
                    f"Status: {status_code} | Duration: {duration:.2f}ms"
                )

            await original_send(message)

        await self.app(scope, receive, custom_send)


def log_request(request_id: str, method: str, path: str,
                status_code: int, duration_ms: float):
    """Log an HTTP request summary."""
    logger = logging.getLogger("request")
    logger.info(
        f"Request | ID: {request_id} | {method} {path} | "
        f"Status: {status_code} | Duration: {duration_ms:.2f}ms"
    )
