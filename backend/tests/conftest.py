"""Test configuration and fixtures."""

import pytest
import tempfile
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from ..db.base import Base
from ..app import app


@pytest.fixture(scope="session")
def test_engine():
    """Create test database engine."""
    # Use in-memory SQLite for tests
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    return engine


@pytest.fixture(scope="function")
def test_db(test_engine):
    """Create test database session."""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
def client(test_db):
    """Create test client."""
    def override_get_db():
        try:
            yield test_db
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture
def sample_topic():
    """Sample topic data."""
    return {
        "id": "test-topic",
        "name": "Test Topic",
        "description": "A test topic for unit tests",
        "keywords": ["test", "example", "demo"]
    }


@pytest.fixture
def sample_signal_event():
    """Sample signal event data."""
    return {
        "id": "test-event-1",
        "source": "arxiv",
        "source_id": "test-paper-1",
        "title": "Test Paper Title",
        "description": "A test paper for unit tests",
        "timestamp": "2024-01-01T00:00:00Z",
        "magnitude": 1.0,
        "metadata": {"test": True}
    }
