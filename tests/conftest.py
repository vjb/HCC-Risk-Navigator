"""
tests/conftest.py — Shared pytest fixtures for HCC Risk Navigator.

Uses a per-test in-memory SQLite database with transaction rollback isolation
to ensure each test starts with a clean slate.
"""
from __future__ import annotations

import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.models import Base


@pytest.fixture(scope="function")
def db_engine(tmp_path):
    """Fresh SQLite DB per test function."""
    db_path = tmp_path / "test_ehr.sqlite"
    engine = create_engine(f"sqlite:///{db_path}", echo=False)
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(db_engine):
    """SQLAlchemy session scoped to a single test function."""
    with Session(db_engine) as session:
        yield session
