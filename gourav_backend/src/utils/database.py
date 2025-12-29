"""
Database configuration and connection management.
Provides SQLAlchemy engine setup, session management, and database initialization.
"""

import logging
import os
from contextlib import contextmanager
from typing import Generator, Optional

from dotenv import load_dotenv
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from src.models.db_models import Base

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./patient_risk_dev.db")
DATABASE_URL_TEST = os.getenv("DATABASE_URL_TEST", "sqlite:///./patient_risk_test.db")

# Global variables for database components
engine: Optional[Engine] = None
SessionLocal: Optional[sessionmaker] = None


def get_database_url(test_mode: bool = False) -> str:
    """Get the appropriate database URL based on mode."""
    return DATABASE_URL_TEST if test_mode else DATABASE_URL


def create_database_engine(database_url: str) -> Engine:
    """
    Create SQLAlchemy engine with appropriate configuration.
    
    Args:
        database_url: Database connection URL
        
    Returns:
        Configured SQLAlchemy engine
    """
    if database_url.startswith("sqlite"):
        # SQLite specific configuration
        engine = create_engine(
            database_url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            echo=os.getenv("SQL_ECHO", "false").lower() == "true"
        )
        
        # Enable foreign key constraints for SQLite
        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
            
    else:
        # PostgreSQL/MySQL configuration
        engine = create_engine(
            database_url,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
            echo=os.getenv("SQL_ECHO", "false").lower() == "true"
        )
    
    return engine


def init_database(test_mode: bool = False, force_recreate: bool = False) -> None:
    """
    Initialize database connection and create tables.
    
    Args:
        test_mode: Whether to use test database
        force_recreate: Whether to drop and recreate all tables
    """
    global engine, SessionLocal

    database_url = get_database_url(test_mode)
    
    try:
        # Create engine
        engine = create_database_engine(database_url)
        
        # Create session factory
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        # Create or recreate tables
        if force_recreate:
            logger.info("Dropping all tables...")
            Base.metadata.drop_all(bind=engine)
            
        logger.info("Creating database tables...")
        Base.metadata.create_all(bind=engine)
        
        # Verify database connection
        with engine.connect() as conn:
            if database_url.startswith("sqlite"):
                result = conn.execute(text("SELECT 1"))
            else:
                result = conn.execute(text("SELECT 1"))
            result.fetchone()
            
        logger.info(f"📊 Database initialized successfully: {database_url}")
        
    except SQLAlchemyError as e:
        logger.error(f"Failed to initialize database: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during database initialization: {e}")
        raise


def get_db() -> Generator[Session, None, None]:
    """
    Dependency function to get database session.
    This will be used by FastAPI dependency injection.
    
    Yields:
        Database session
    """
    if SessionLocal is None:
        init_database()

    db = SessionLocal()
    try:
        yield db
    except SQLAlchemyError as e:
        logger.error(f"Database session error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """
    Context manager for database sessions.
    Useful for non-FastAPI contexts.
    
    Yields:
        Database session
    """
    if SessionLocal is None:
        init_database()
        
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except SQLAlchemyError as e:
        logger.error(f"Database session error: {e}")
        db.rollback()
        raise
    except Exception as e:
        logger.error(f"Unexpected error in database session: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def close_database() -> None:
    """Close database connections and cleanup resources."""
    global engine, SessionLocal
    
    if engine:
        try:
            engine.dispose()
            logger.info("📊 Database connections closed")
        except Exception as e:
            logger.error(f"Error closing database connections: {e}")
        finally:
            engine = None
            SessionLocal = None


def check_database_health() -> bool:
    """
    Check if database is accessible and healthy.
    
    Returns:
        True if database is healthy, False otherwise
    """
    if engine is None:
        return False
        
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except SQLAlchemyError as e:
        logger.error(f"Database health check failed: {e}")
        return False


def reset_database(test_mode: bool = False) -> None:
    """
    Reset database by dropping and recreating all tables.
    Useful for testing and development.
    
    Args:
        test_mode: Whether to reset test database
    """
    global engine, SessionLocal
    
    # Close existing connections
    if engine:
        engine.dispose()
        
    # Reinitialize with force recreate
    init_database(test_mode=test_mode, force_recreate=True)


# For testing purposes
def get_test_db() -> Generator[Session, None, None]:
    """Get a test database session."""
    if SessionLocal is None:
        init_database(test_mode=True)

    db = SessionLocal()
    try:
        yield db
    except SQLAlchemyError as e:
        logger.error(f"Test database session error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def create_test_database() -> None:
    """Initialize test database with clean state."""
    reset_database(test_mode=True)
