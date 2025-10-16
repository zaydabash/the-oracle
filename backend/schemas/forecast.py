"""Forecast schemas for The Oracle API."""

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class ForecastPoint(BaseModel):
    """Individual forecast point."""
    date: str
    yhat: float
    yhat_lower: Optional[float] = None
    yhat_upper: Optional[float] = None


class TopicForecastBase(BaseModel):
    """Base topic forecast schema."""
    topic_id: str
    horizon_days: int = Field(..., ge=1, le=365)
    forecast_curve: List[ForecastPoint] = Field(default_factory=list)
    surge_score: float = Field(default=0.0, ge=0.0, le=1.0)
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0)
    model_type: str = Field(default="ARIMA", max_length=100)
    model_params: Dict = Field(default_factory=dict)
    model_metrics: Dict = Field(default_factory=dict)


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
    topic_id: Optional[str] = None
    horizon_days: Optional[int] = Field(None, ge=1, le=365)
    forecast_curve: Optional[List[ForecastPoint]] = None
    surge_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    model_type: Optional[str] = Field(None, max_length=100)
    model_params: Optional[Dict] = None
    model_metrics: Optional[Dict] = None


class ForecastSummary(BaseModel):
    """Forecast summary for dashboard."""
    topic_id: str
    topic_name: str
    horizon_30d: Optional[float] = None
    horizon_90d: Optional[float] = None
    horizon_180d: Optional[float] = None
    surge_score: float = 0.0
    confidence: float = 0.0
    growth_rate: Optional[float] = None
    
    class Config:
        from_attributes = True


class ForecastLeaderboard(BaseModel):
    """Forecast leaderboard response."""
    forecasts: List[ForecastSummary]
    total: int
    generated_at: datetime
    
    class Config:
        from_attributes = True


class TopicForecastDetail(TopicForecastResponse):
    """Detailed forecast information."""
    topic_name: str
    latest_velocity: Optional[float] = None
    velocity_trend: List[float] = Field(default_factory=list)
    forecast_growth_rate: Optional[float] = None
    model_performance: Dict = Field(default_factory=dict)
    
    class Config:
        from_attributes = True
