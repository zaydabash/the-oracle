"""Forecast models for The Oracle."""

from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from ..db.base import Base


class TopicForecast(Base):
    """Topic forecast model representing predictions for topic trends."""

    __tablename__ = "topic_forecasts"

    id = Column(String(255), primary_key=True, index=True)
    topic_id = Column(String(255), ForeignKey("topics.id"), nullable=False, index=True)
    horizon_days = Column(Integer, nullable=False, index=True)

    # Forecast data
    forecast_curve = Column(JSON, nullable=False, default=list)
    surge_score = Column(Float, nullable=False, default=0.0)
    confidence_score = Column(Float, nullable=False, default=0.0)

    # Model metadata
    model_type = Column(String(100), nullable=False, default="ARIMA")
    model_params = Column(JSON, nullable=True, default=dict)
    model_metrics = Column(JSON, nullable=True, default=dict)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    topic = relationship("Topic", back_populates="topic_forecasts")

    def __repr__(self) -> str:
        return f"<TopicForecast(topic_id='{self.topic_id}', horizon_days={self.horizon_days}, surge_score={self.surge_score})>"

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "topic_id": self.topic_id,
            "horizon_days": self.horizon_days,
            "forecast_curve": self.forecast_curve,
            "surge_score": self.surge_score,
            "confidence_score": self.confidence_score,
            "model_type": self.model_type,
            "model_params": self.model_params,
            "model_metrics": self.model_metrics,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @property
    def forecast_points(self) -> list[dict]:
        """Get forecast curve as list of points."""
        return self.forecast_curve or []

    @property
    def latest_forecast_value(self) -> float | None:
        """Get the latest forecasted value."""
        if not self.forecast_points:
            return None
        return self.forecast_points[-1].get("yhat", 0.0)

    @property
    def forecast_growth_rate(self) -> float | None:
        """Calculate growth rate from forecast."""
        if not self.forecast_points or len(self.forecast_points) < 2:
            return None

        first_value = self.forecast_points[0].get("yhat", 0.0)
        last_value = self.forecast_points[-1].get("yhat", 0.0)

        if first_value == 0:
            return 0.0

        return (last_value - first_value) / first_value
