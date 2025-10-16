"""Configuration management for The Oracle."""

import json
from pathlib import Path
from typing import Dict, List, Literal, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Database
    database_url: str = Field(
        default="postgresql+psycopg2://oracle:oracle@localhost:5432/oracle",
        env="DATABASE_URL"
    )
    
    # Oracle Mode
    oracle_mode: Literal["mock", "live"] = Field(default="mock", env="ORACLE_MODE")
    
    # Data Source Configuration
    arxiv_categories: List[str] = Field(
        default=["cs.AI", "cs.CL", "cs.LG", "stat.ML"],
        env="ARXIV_CATEGORIES"
    )
    github_token: Optional[str] = Field(default=None, env="GITHUB_TOKEN")
    crunchbase_api_key: Optional[str] = Field(default=None, env="CRUNCHBASE_API_KEY")
    jobs_feed_urls: List[str] = Field(
        default=[
            "https://weworkremotely.com/categories/remote-programming-jobs.rss",
            "https://remoteok.io/remote-dev-jobs.rss"
        ],
        env="JOBS_FEED_URLS"
    )
    
    # Topic Configuration
    topic_keywords_json: str = Field(default="./data/topic_keywords.json", env="TOPIC_KEYWORDS_JSON")
    
    # API Configuration
    api_host: str = Field(default="0.0.0.0", env="API_HOST")
    api_port: int = Field(default=8000, env="API_PORT")
    cors_origins: List[str] = Field(
        default=["http://localhost:5173", "http://localhost:3000"],
        env="CORS_ORIGINS"
    )
    
    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = Field(default="json", env="LOG_FORMAT")
    
    # Forecasting
    forecast_horizons: List[int] = Field(default=[30, 90, 180], env="FORECAST_HORIZONS")
    surge_score_weights: Dict[str, float] = Field(
        default={
            "velocity_growth": 0.4,
            "momentum": 0.3,
            "z_spike": 0.2,
            "convergence": 0.1
        },
        env="SURGE_SCORE_WEIGHTS"
    )
    
    # Development
    debug: bool = Field(default=True, env="DEBUG")
    reload: bool = Field(default=True, env="RELOAD")
    
    @field_validator("arxiv_categories", mode="before")
    @classmethod
    def parse_arxiv_categories(cls, v):
        if isinstance(v, str):
            return [cat.strip() for cat in v.split(",")]
        return v
    
    @field_validator("jobs_feed_urls", mode="before")
    @classmethod
    def parse_jobs_feed_urls(cls, v):
        if isinstance(v, str):
            return [url.strip() for url in v.split(",")]
        return v
    
    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    @field_validator("forecast_horizons", mode="before")
    @classmethod
    def parse_forecast_horizons(cls, v):
        if isinstance(v, str):
            return [int(h.strip()) for h in v.split(",")]
        return v
    
    @field_validator("surge_score_weights", mode="before")
    @classmethod
    def parse_surge_score_weights(cls, v):
        if isinstance(v, str):
            return json.loads(v)
        return v
    
    @property
    def is_mock_mode(self) -> bool:
        """Check if running in mock mode."""
        return self.oracle_mode == "mock"
    
    @property
    def is_live_mode(self) -> bool:
        """Check if running in live mode."""
        return self.oracle_mode == "live"
    
    @property
    def topic_keywords_path(self) -> Path:
        """Get the path to topic keywords JSON file."""
        return Path(self.topic_keywords_json)
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()
