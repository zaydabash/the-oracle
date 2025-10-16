"""Database session management."""

from contextlib import contextmanager
from typing import Generator

from sqlalchemy.orm import Session

from .base import SessionLocal


@contextmanager
def get_db() -> Generator[Session, None, None]:
    """Get database session with automatic cleanup."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db_session() -> Session:
    """Get a database session (for dependency injection)."""
    return SessionLocal()
