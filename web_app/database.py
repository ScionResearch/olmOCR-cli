"""Database configuration and utilities."""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from contextlib import contextmanager
from .models import Base

# Database configuration from environment variables
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://ocr_user:ocr_password@postgres:5432/ocr_db"
)

# For development, fallback to SQLite
if DATABASE_URL.startswith("postgresql://"):
    # Production PostgreSQL configuration
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_recycle=300,
        echo=os.getenv("DEBUG", "false").lower() == "true"
    )
else:
    # Development SQLite configuration
    engine = create_engine(
        "sqlite:///./ocr_jobs.db",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=True
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def create_tables():
    """Create all database tables."""
    Base.metadata.create_all(bind=engine)

@contextmanager
def get_db_session() -> Session:
    """Get database session with automatic cleanup."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

def get_db() -> Session:
    """Dependency for FastAPI to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()