"""Signal event model for The Oracle."""

from datetime import datetime
from typing import Dict, Literal, Optional

from sqlalchemy import Column, DateTime, Float, ForeignKey, JSON, String, Text
from sqlalchemy.orm import relationship

from ..db.base import Base

SourceType = Literal["arxiv", "github", "jobs", "funding"]


class SignalEvent(Base):
    """Signal event model representing individual data points from external sources."""
    
    __tablename__ = "signal_events"
    
    id = Column(String(255), primary_key=True, index=True)
    source = Column(String(50), nullable=False, index=True)
    source_id = Column(String(255), nullable=False)
    topic_id = Column(String(255), ForeignKey("topics.id"), nullable=True, index=True)
    title = Column(String(500), nullable=False)
    url = Column(String(1000), nullable=True)
    description = Column(Text, nullable=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    magnitude = Column(Float, nullable=False, default=1.0)
    metadata = Column(JSON, nullable=True, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    topic = relationship("Topic", back_populates="signal_events")
    
    def __repr__(self) -> str:
        return f"<SignalEvent(id='{self.id}', source='{self.source}', topic_id='{self.topic_id}')>"
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "source": self.source,
            "source_id": self.source_id,
            "topic_id": self.topic_id,
            "title": self.title,
            "url": self.url,
            "description": self.description,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "magnitude": self.magnitude,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
