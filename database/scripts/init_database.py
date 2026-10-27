#!/usr/bin/env python3
"""Database initialization script for RealityShield-AI."""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.app.db.database import init_db, create_tables, Base, SessionLocal, get_db
from backend.app.models.user import UserInDB, UserRole
from backend.app.services.auth_service import auth_service
from backend.app.core.config import settings
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_initial_data():
    """Create initial database tables and seed data."""
    try:
        logger.info("Initializing database...")
        init_db()
        create_tables()

        # Create initial admin user if not exists
        db = SessionLocal()
        try:
            # Check if admin exists
            result = db.execute(text("SELECT 1 FROM users WHERE username = 'admin'")).fetchone()
            if not result:
                admin_user = UserInDB(
                    username="admin",
                    email="admin@realityshield.ai",
                    hashed_password=auth_service.hash_password("admin123"),
                    full_name="System Administrator",
                    is_active=True,
                    is_verified=True
                )
                db.add(admin_user)
                db.commit()
                logger.info("Created admin user")

                # Create admin role
                admin_role = UserRole(
                    user_id=admin_user.id,
                    role="admin",
                    permissions=["all"],
                    granted_by=admin_user.id
                )
                db.add(admin_role)
                db.commit()
                logger.info("Created admin role")
            else:
                logger.info("Admin user already exists")

        except Exception as e:
            db.rollback()
            logger.error(f"Error creating initial data: {e}")
            raise
        finally:
            db.close()

        logger.info("Database initialization completed successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise


if __name__ == "__main__":
    create_initial_data()