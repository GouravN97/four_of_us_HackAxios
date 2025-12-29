"""
Database configuration and connection management.
This module will be expanded in task 3.1 with full implementation.
"""

import os
from typing import Optional

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.models.db_models import Base

# Load environment variables
load_dotenv()

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./patient_risk_dev.db")
DATABASE_URL_TEST = os.getenv("DATABASE_URL_TEST", "sqlite:///./patient_risk_test.db")

# Global variables for database components
engine = None
SessionLocal = None


def get_database_url(test_mode: bool = False) -> str:
    """Get the appropriate database URL based on mode."""
    return DATABASE_URL_TEST if test_mode else DATABASE_URL


def init_database(test_mode: bool = False) -> None:
    """
    Initialize database connection and create tables.
    This is a placeholder implementation - full implementation in task 3.1.
    """
    global engine, SessionLocal

    database_url = get_database_url(test_mode)

    # Create engine
    if database_url.startswith("sqlite"):
        engine = create_engine(
            database_url, connect_args={"check_same_thread": False}  # SQLite specific
        )
    else:
        engine = create_engine(database_url)

    # Create session factory
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # Create tables
    Base.metadata.create_all(bind=engine)

    print(f"📊 Database initialized: {database_url}")


def get_db() -> Session:
    """
    Dependency function to get database session.
    This will be used by FastAPI dependency injection.
    """
    if SessionLocal is None:
        init_database()

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def close_database() -> None:
    """Close database connections."""
    global engine
    if engine:
        engine.dispose()
        print("📊 Database connections closed")


# For testing purposes
def get_test_db() -> Session:
    """Get a test database session."""
    if SessionLocal is None:
        init_database(test_mode=True)

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
