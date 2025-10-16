"""API dependencies for The Oracle."""

from collections.abc import Generator

from sqlalchemy.orm import Session

from ..db.session import get_db


def get_database() -> Generator[Session, None, None]:
    """Get database session dependency."""
    db = next(get_db())
    try:
        yield db
    finally:
        db.close()
