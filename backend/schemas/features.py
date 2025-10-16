"""Feature schemas for The Oracle API."""

from datetime import date, datetime

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
    topic_id: str | None = None
    date: date | None = None


class TopicFeaturesList(BaseModel):
    """Schema for topic features list response."""
    features: list[TopicFeaturesResponse]
    total: int
    start_date: date
    end_date: date


class FeatureMatrix(BaseModel):
    """Feature matrix for analysis."""
    topic_ids: list[str]
    dates: list[date]
    velocity_matrix: list[list[float]]
    acceleration_matrix: list[list[float]]
    convergence_matrix: list[list[float]]
    z_spike_matrix: list[list[float]]

    class Config:
        from_attributes = True
