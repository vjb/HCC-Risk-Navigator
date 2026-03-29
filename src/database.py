"""
SQLAlchemy engine and session factory.
Uses DATABASE_URL from .env, defaulting to local SQLite.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

load_dotenv()

# Default to local SQLite; override via DATABASE_URL env var
_DEFAULT_DB = "sqlite:///data/mock_ehr.sqlite"
DATABASE_URL: str = os.getenv("DATABASE_URL", _DEFAULT_DB)

# Ensure the data/ directory exists for SQLite file-based DBs
if DATABASE_URL.startswith("sqlite:///"):
    db_path = Path(DATABASE_URL.replace("sqlite:///", ""))
    db_path.parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
    echo=False,
)

SessionLocal: sessionmaker[Session] = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)


def get_session() -> Session:
    """Return a new database session. Caller is responsible for closing."""
    return SessionLocal()


def init_db() -> None:
    """Create all tables (idempotent). Called by seed_db and tests."""
    from src.models import Base  # noqa: PLC0415 — local import avoids circular deps
    Base.metadata.create_all(bind=engine)
