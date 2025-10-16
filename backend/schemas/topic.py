"""Topic schemas for The Oracle API."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class TopicBase(BaseModel):
    """Base topic schema."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    keywords: List[str] = Field(default_factory=list)


class TopicCreate(TopicBase):
    """Schema for creating a topic."""
    pass


class TopicUpdate(TopicBase):
    """Schema for updating a topic."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)


class TopicResponse(TopicBase):
    """Schema for topic response."""
    id: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class TopicWithStats(TopicResponse):
    """Topic with aggregated statistics."""
    latest_velocity: Optional[float] = None
    latest_acceleration: Optional[float] = None
    latest_surge_score: Optional[float] = None
    mention_count_7d: int = 0
    mention_count_30d: int = 0
    
    class Config:
        from_attributes = True


class TopicLeaderboardItem(BaseModel):
    """Topic leaderboard item."""
    rank: int
    topic: TopicResponse
    surge_score: float
    velocity: float
    acceleration: float
    mention_count_30d: int
    sparkline_data: List[float] = Field(default_factory=list)
    
    class Config:
        from_attributes = True


class TopicDetail(TopicResponse):
    """Detailed topic information."""
    recent_events_count: int = 0
    velocity_trend: List[float] = Field(default_factory=list)
    acceleration_trend: List[float] = Field(default_factory=list)
    forecast_curves: List[dict] = Field(default_factory=list)
    contributing_sources: dict = Field(default_factory=dict)
    
    class Config:
        from_attributes = True
