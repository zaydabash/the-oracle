"""Feature schemas for The Oracle API."""

from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class TopicFeaturesBase(BaseModel):
    """Base topic features schema."""
    topic_id: str
    date: date
    
    # Count metrics
    mention_count_total: int = Field(default=0, ge=0)
    mention_count_arxiv: int = Field(default=0, ge=0)
    mention_count_github: int = Field(default=0, ge=0)
    mention_count_jobs: int = Field(default=0, ge=0)
    mention_count_funding: int = Field(default=0, ge=0)
    
    # Velocity metrics
    velocity: float = Field(default=0.0)
    acceleration: float = Field(default=0.0)
    z_spike: float = Field(default=0.0)
    convergence: float = Field(default=0.0)
    
    # Additional metrics
    magnitude_sum: float = Field(default=0.0)
    unique_sources: int = Field(default=0, ge=0)


class TopicFeaturesResponse(TopicFeaturesBase):
    """Schema for topic features response."""
    id: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class TopicFeaturesCreate(TopicFeaturesBase):
    """Schema for creating topic features."""
    pass


class TopicFeaturesUpdate(TopicFeaturesBase):
    """Schema for updating topic features."""
    topic_id: Optional[str] = None
    date: Optional[date] = None


class TopicFeaturesList(BaseModel):
    """Schema for topic features list response."""
    features: List[TopicFeaturesResponse]
    total: int
    start_date: date
    end_date: date


class FeatureMatrix(BaseModel):
    """Feature matrix for analysis."""
    topic_ids: List[str]
    dates: List[date]
    velocity_matrix: List[List[float]]
    acceleration_matrix: List[List[float]]
    convergence_matrix: List[List[float]]
    z_spike_matrix: List[List[float]]
    
    class Config:
        from_attributes = True
