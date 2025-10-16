"""Signal event schemas for The Oracle API."""

from datetime import datetime
from typing import Dict, Literal, Optional

from pydantic import BaseModel, Field

SourceType = Literal["arxiv", "github", "jobs", "funding"]


class SignalEventBase(BaseModel):
    """Base signal event schema."""
    source: SourceType
    source_id: str = Field(..., min_length=1, max_length=255)
    title: str = Field(..., min_length=1, max_length=500)
    url: Optional[str] = Field(None, max_length=1000)
    description: Optional[str] = None
    timestamp: datetime
    magnitude: float = Field(default=1.0, ge=0.0)
    metadata: Dict = Field(default_factory=dict)


class SignalEventCreate(SignalEventBase):
    """Schema for creating a signal event."""
    topic_id: Optional[str] = None


class SignalEventResponse(SignalEventBase):
    """Schema for signal event response."""
    id: str
    topic_id: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


class SignalEventFilter(BaseModel):
    """Schema for filtering signal events."""
    topic_id: Optional[str] = None
    source: Optional[SourceType] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    min_magnitude: Optional[float] = Field(None, ge=0.0)
    limit: int = Field(default=100, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)


class SignalEventList(BaseModel):
    """Schema for signal event list response."""
    events: list[SignalEventResponse]
    total: int
    limit: int
    offset: int
    has_more: bool
