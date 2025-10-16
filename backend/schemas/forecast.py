"""Forecast schemas for The Oracle API."""

from datetime import datetime

from pydantic import BaseModel, Field


class ForecastPoint(BaseModel):
    """Individual forecast point."""
    date: str
    yhat: float
    yhat_lower: float | None = None
    yhat_upper: float | None = None


class TopicForecastBase(BaseModel):
    """Base topic forecast schema."""
    topic_id: str
    horizon_days: int = Field(..., ge=1, le=365)
    forecast_curve: list[ForecastPoint] = Field(default_factory=list)
    surge_score: float = Field(default=0.0, ge=0.0, le=1.0)
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0)
    model_type: str = Field(default="ARIMA", max_length=100)
    model_params: dict = Field(default_factory=dict)
    model_metrics: dict = Field(default_factory=dict)


class TopicForecastCreate(TopicForecastBase):
    """Schema for creating a topic forecast."""
    pass


class TopicForecastResponse(TopicForecastBase):
    """Schema for topic forecast response."""
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TopicForecastUpdate(TopicForecastBase):
    """Schema for updating a topic forecast."""
    topic_id: str | None = None
    horizon_days: int | None = Field(None, ge=1, le=365)
    forecast_curve: list[ForecastPoint] | None = None
    surge_score: float | None = Field(None, ge=0.0, le=1.0)
    confidence_score: float | None = Field(None, ge=0.0, le=1.0)
    model_type: str | None = Field(None, max_length=100)
    model_params: dict | None = None
    model_metrics: dict | None = None


class ForecastSummary(BaseModel):
    """Forecast summary for dashboard."""
    topic_id: str
    topic_name: str
    horizon_30d: float | None = None
    horizon_90d: float | None = None
    horizon_180d: float | None = None
    surge_score: float = 0.0
    confidence: float = 0.0
    growth_rate: float | None = None

    class Config:
        from_attributes = True


class ForecastLeaderboard(BaseModel):
    """Forecast leaderboard response."""
    forecasts: list[ForecastSummary]
    total: int
    generated_at: datetime

    class Config:
        from_attributes = True


class TopicForecastDetail(TopicForecastResponse):
    """Detailed forecast information."""
    topic_name: str
    latest_velocity: float | None = None
    velocity_trend: list[float] = Field(default_factory=list)
    forecast_growth_rate: float | None = None
    model_performance: dict = Field(default_factory=dict)

    class Config:
        from_attributes = True
