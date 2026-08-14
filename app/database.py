"""
Database configuration and session management.
Supports both PostgreSQL (Neon) for production and SQLite for local dev.
"""

import os
from dotenv import load_dotenv
from sqlmodel import SQLModel, Session, create_engine

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./patients.db")

# Engine configuration
# pool_pre_ping=True handles Neon's scale-to-zero reconnections gracefully
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    connect_args=connect_args,
    echo=False,
)


def create_db_and_tables():
    """Create all tables defined by SQLModel metadata."""
    SQLModel.metadata.create_all(engine)


def get_session():
    """FastAPI dependency that provides a database session."""
    with Session(engine) as session:
        yield session
