"""Feature models for The Oracle."""

from datetime import datetime

from sqlalchemy import Column, Date, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from ..db.base import Base


class TopicFeatures(Base):
    """Topic features model representing aggregated metrics per topic per day."""

    __tablename__ = "topic_features"

    id = Column(String(255), primary_key=True, index=True)
    topic_id = Column(String(255), ForeignKey("topics.id"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)

    # Count metrics
    mention_count_total = Column(Integer, nullable=False, default=0)
    mention_count_arxiv = Column(Integer, nullable=False, default=0)
    mention_count_github = Column(Integer, nullable=False, default=0)
    mention_count_jobs = Column(Integer, nullable=False, default=0)
    mention_count_funding = Column(Integer, nullable=False, default=0)

    # Velocity metrics
    velocity = Column(Float, nullable=False, default=0.0)
    acceleration = Column(Float, nullable=False, default=0.0)
    z_spike = Column(Float, nullable=False, default=0.0)
    convergence = Column(Float, nullable=False, default=0.0)

    # Additional metrics
    magnitude_sum = Column(Float, nullable=False, default=0.0)
    unique_sources = Column(Integer, nullable=False, default=0)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    topic = relationship("Topic", back_populates="topic_features")

    def __repr__(self) -> str:
        return f"<TopicFeatures(topic_id='{self.topic_id}', date='{self.date}', velocity={self.velocity})>"

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "topic_id": self.topic_id,
            "date": self.date.isoformat() if self.date else None,
            "mention_count_total": self.mention_count_total,
            "mention_count_arxiv": self.mention_count_arxiv,
            "mention_count_github": self.mention_count_github,
            "mention_count_jobs": self.mention_count_jobs,
            "mention_count_funding": self.mention_count_funding,
            "velocity": self.velocity,
            "acceleration": self.acceleration,
            "z_spike": self.z_spike,
            "convergence": self.convergence,
            "magnitude_sum": self.magnitude_sum,
            "unique_sources": self.unique_sources,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
