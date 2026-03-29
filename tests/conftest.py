"""
Shared pytest fixtures for the Auto-Auth Pre-Cog test suite.
Uses an in-memory SQLite database so tests never touch disk.
"""
from __future__ import annotations

import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Point all tests at in-memory SQLite — never touches data/mock_ehr.sqlite
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from src.models import Base  # noqa: E402


@pytest.fixture(scope="session")
def engine():
    """Session-scoped in-memory SQLite engine."""
    _engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=_engine)
    yield _engine
    _engine.dispose()


@pytest.fixture()
def db_session(engine):
    """
    Function-scoped DB session that rolls back after every test.
    Guarantees test isolation without re-creating tables.
    """
    connection = engine.connect()
    transaction = connection.begin()
    Session = sessionmaker(bind=connection)
    session = Session()

    yield session

    session.close()
    transaction.rollback()
    connection.close()
