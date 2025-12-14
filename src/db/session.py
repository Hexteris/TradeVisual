# src/db/session.py
"""Database session factory and initialization."""

import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel, create_engine, Session
from pathlib import Path

# Get database URL from environment, default to local SQLite
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./trading_journal.db")

# Convert sqlite:// to file path for local development
if DATABASE_URL.startswith("sqlite://"):
    db_path = DATABASE_URL.replace("sqlite:///", "")
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

# Use synchronous engine for Streamlit (no async support needed yet)
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
    echo=False,
)


def create_db_and_tables():
    """Create all tables if they don't exist."""
    SQLModel.metadata.create_all(engine)


def get_session() -> Session:
    """Get a new database session."""
    return Session(engine)


def init_db():
    """Initialize database on startup."""
    create_db_and_tables()
