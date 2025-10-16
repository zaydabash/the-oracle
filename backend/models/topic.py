"""Topic model for The Oracle."""

from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, String, Text
from sqlalchemy.orm import relationship

from ..db.base import Base


class Topic(Base):
    """Topic model representing a technology domain or trend."""

    __tablename__ = "topics"

    id = Column(String(255), primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    keywords = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    signal_events = relationship("SignalEvent", back_populates="topic")
    topic_features = relationship("TopicFeatures", back_populates="topic")
    topic_forecasts = relationship("TopicForecast", back_populates="topic")

    def __repr__(self) -> str:
        return f"<Topic(id='{self.id}', name='{self.name}')>"

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "keywords": self.keywords,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
