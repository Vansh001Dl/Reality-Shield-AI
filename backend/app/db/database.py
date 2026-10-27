"""Database configuration and connection management for RealityShield-AI."""

from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import QueuePool
from sqlalchemy.engine import Engine, make_url
from contextlib import contextmanager
import logging
from typing import Generator

from app.core.config import settings
from app.core.logging import configure_logging

configure_logging()
logger = logging.getLogger(__name__)

# Database engine
_engine: Engine = None
SessionLocal = None
Base = declarative_base()
_async_engine = None
AsyncSessionLocal = None


def _async_database_url(database_url: str) -> str:
    if database_url.startswith("postgresql+psycopg2://"):
        return database_url.replace("postgresql+psycopg2://", "postgresql+asyncpg://", 1)
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if database_url.startswith("sqlite:///"):
        return database_url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
    return database_url


def get_async_sessionmaker():
    """Return the async session factory for the configured database."""
    global _async_engine, AsyncSessionLocal
    if AsyncSessionLocal is None:
        from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
        url = _async_database_url(settings.database_url)
        _async_engine = create_async_engine(url, pool_pre_ping=True)
        AsyncSessionLocal = async_sessionmaker(_async_engine, expire_on_commit=False, class_=AsyncSession)
    return AsyncSessionLocal


async def get_async_db():
    """FastAPI dependency yielding an async SQLAlchemy session."""
    async with get_async_sessionmaker()() as session:
        yield session


def _create_database_engine(database_url: str) -> Engine:
    is_sqlite = database_url.startswith("sqlite")
    if is_sqlite:
        database_path = Path(database_url.removeprefix("sqlite:///"))
        database_path.parent.mkdir(parents=True, exist_ok=True)

    return create_engine(
        database_url,
        poolclass=QueuePool,
        pool_size=10,
        max_overflow=20,
        pool_timeout=30,
        pool_recycle=3600,
        echo=False,
        connect_args={"check_same_thread": False} if is_sqlite else {
            "connect_timeout": 30,
            "application_name": "RealityShield-AI",
        },
    )


def _create_user_table(engine: Engine) -> None:
    with engine.connect():
        logger.info("Database connection established successfully")
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id VARCHAR(64) PRIMARY KEY,
                    username VARCHAR(50) NOT NULL UNIQUE,
                    email VARCHAR(320) NOT NULL UNIQUE,
                    full_name VARCHAR(100),
                    hashed_password VARCHAR(255) NOT NULL,
                    is_active BOOLEAN NOT NULL DEFAULT TRUE,
                    is_verified BOOLEAN NOT NULL DEFAULT FALSE,
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    role VARCHAR(32) NOT NULL DEFAULT 'viewer'
                )
                """
            )
        )


def init_db():
    """Initialize the configured database, with a safe SQLite fallback when the primary DB is unavailable."""
    global _engine, SessionLocal

    database_url = settings.database_url
    engine = _create_database_engine(database_url)
    try:
        _create_user_table(engine)
    except Exception as e:
        engine.dispose()
        parsed_url = make_url(database_url)
        fallback_to_sqlite = (
            parsed_url.drivername.startswith("postgresql")
            or parsed_url.drivername.startswith("postgresql+psycopg")
            or database_url.startswith("sqlite") is False
        )

        if not fallback_to_sqlite:
            logger.error("Database connection failed: %s", e)
            raise

        database_path = Path(__file__).resolve().parents[2] / "data" / "users.sqlite3"
        database_url = f"sqlite:///{database_path.as_posix()}"
        logger.warning(
            "Primary database is unavailable; falling back to SQLite at %s. Error: %s",
            database_path,
            e,
        )
        engine = _create_database_engine(database_url)
        try:
            _create_user_table(engine)
        except Exception:
            engine.dispose()
            logger.exception("SQLite database initialization failed")
            raise

    settings.database_url = database_url
    _engine = engine
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)

    create_tables()


def get_db():
    """Get database session."""
    global SessionLocal
    if SessionLocal is None:
        init_db()

    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@contextmanager
def get_db_context() -> Generator:
    """Context manager for database sessions."""
    global SessionLocal
    if SessionLocal is None:
        init_db()
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def create_tables():
    """Create all tables for the application schema."""
    try:
        from app.db import models  # noqa: F401

        if _engine is None:
            init_db()
        Base.metadata.create_all(bind=_engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Table creation failed: {e}")
        raise


def drop_tables():
    """Drop all tables (use with caution)."""
    try:
        Base.metadata.drop_all(bind=_engine)
        logger.info("Database tables dropped successfully")
    except Exception as e:
        logger.error(f"Table drop failed: {e}")
        raise


def get_database_url():
    """Get current database URL (without credentials)."""
    return settings.database_url
