"""Topics router for The Oracle."""


from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Dict

from ...core.logging import get_logger
from ...db.session import get_db
from ...forecasting.ranker import SurgeRanker
from ...models.features import TopicFeatures
from ...models.forecast import TopicForecast
from ...models.signal_event import SignalEvent
from ...models.topic import Topic
from ...narratives.generate import NarrativeGenerator
from ...schemas.topic import TopicDetail, TopicLeaderboardItem, TopicResponse

logger = get_logger(__name__)

router = APIRouter(prefix="/topics", tags=["topics"])


@router.get("/", response_model=list[TopicResponse])
async def list_topics(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """List all topics with basic information."""
    try:
        topics = db.query(Topic).offset(skip).limit(limit).all()
        return topics
    except Exception as e:
        logger.error(f"Error listing topics: {e}")
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get("/leaderboard", response_model=list[TopicLeaderboardItem])
async def get_leaderboard(
    horizon: int = Query(30, ge=1, le=365),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Get topic leaderboard ranked by surge probability."""
    try:
        ranker = SurgeRanker()
        rankings = ranker.rank_topics(horizon_days=horizon, limit=limit)

        if not rankings:
            return []

        # Convert to leaderboard items
        leaderboard_items = []
        for ranking in rankings:
            # Get topic details
            topic = db.query(Topic).filter(Topic.id == ranking["topic_id"]).first()
            if not topic:
                continue

            # Get sparkline data (last 30 days of velocity)
            sparkline_data = _get_sparkline_data(db, ranking["topic_id"])

            # Get mention count for last 30 days
            mention_count_30d = _get_mention_count(db, ranking["topic_id"], days=30)

            leaderboard_item = TopicLeaderboardItem(
                rank=ranking["rank"],
                topic=TopicResponse.from_orm(topic),
                surge_score=ranking["surge_score"],
                velocity=ranking["recent_velocity"],
                acceleration=ranking.get("recent_acceleration", 0),
                mention_count_30d=mention_count_30d,
                sparkline_data=sparkline_data
            )

            leaderboard_items.append(leaderboard_item)

        return leaderboard_items

    except Exception as e:
        logger.error(f"Error getting leaderboard: {e}")
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get("/{topic_id}", response_model=TopicDetail)
async def get_topic_detail(
    topic_id: str,
    db: Session = Depends(get_db)
):
    """Get detailed information for a specific topic."""
    try:
        # Get topic
        topic = db.query(Topic).filter(Topic.id == topic_id).first()
        if not topic:
            raise HTTPException(status_code=404, detail="Topic not found")

        # Get recent events count
        recent_events_count = db.query(SignalEvent).filter(
            SignalEvent.topic_id == topic_id
        ).count()

        # Get velocity and acceleration trends (last 30 days)
        velocity_trend = _get_velocity_trend(db, topic_id, days=30)
        acceleration_trend = _get_acceleration_trend(db, topic_id, days=30)

        # Get forecast curves for different horizons
        forecast_curves = {}
        for horizon in [30, 90, 180]:
            forecast = db.query(TopicForecast).filter(
                TopicForecast.topic_id == topic_id,
                TopicForecast.horizon_days == horizon
            ).first()

            if forecast:
                forecast_curves[horizon] = forecast.forecast_curve

        # Get contributing sources (last 30 days)
        contributing_sources = _get_contributing_sources(db, topic_id, days=30)

        # Build topic detail
        topic_detail = TopicDetail(
            **topic.to_dict(),
            recent_events_count=recent_events_count,
            velocity_trend=velocity_trend,
            acceleration_trend=acceleration_trend,
            forecast_curves=forecast_curves,
            contributing_sources=contributing_sources
        )

        return topic_detail

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting topic detail for {topic_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get("/{topic_id}/narrative")
async def get_topic_narrative(
    topic_id: str,
    horizon: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db)
):
    """Get narrative summary for a topic."""
    try:
        # Check if topic exists
        topic = db.query(Topic).filter(Topic.id == topic_id).first()
        if not topic:
            raise HTTPException(status_code=404, detail="Topic not found")

        # Generate narrative
        generator = NarrativeGenerator()
        narrative = generator.generate_topic_summary(topic_id, horizon)

        return {
            "topic_id": topic_id,
            "topic_name": topic.name,
            "horizon_days": horizon,
            "narrative": narrative,
            "generated_at": datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating narrative for {topic_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get("/{topic_id}/forecasts")
async def get_topic_forecasts(
    topic_id: str,
    db: Session = Depends(get_db)
):
    """Get all forecasts for a topic."""
    try:
        # Check if topic exists
        topic = db.query(Topic).filter(Topic.id == topic_id).first()
        if not topic:
            raise HTTPException(status_code=404, detail="Topic not found")

        # Get forecasts
        forecasts = db.query(TopicForecast).filter(
            TopicForecast.topic_id == topic_id
        ).all()

        return {
            "topic_id": topic_id,
            "topic_name": topic.name,
            "forecasts": [forecast.to_dict() for forecast in forecasts]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting forecasts for {topic_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error") from e


def _get_sparkline_data(db: Session, topic_id: str, days: int = 30) -> list[float]:
    """Get sparkline data for topic velocity."""
    try:
        from datetime import date, timedelta

        start_date = date.today() - timedelta(days=days)

        features = db.query(TopicFeatures).filter(
            TopicFeatures.topic_id == topic_id,
            TopicFeatures.date >= start_date
        ).order_by(TopicFeatures.date.asc()).all()

        return [f.velocity for f in features]

    except Exception:
        return []


def _get_mention_count(db: Session, topic_id: str, days: int = 30) -> int:
    """Get mention count for topic in specified days."""
    try:
        from datetime import datetime, timedelta

        start_date = datetime.utcnow() - timedelta(days=days)

        count = db.query(SignalEvent).filter(
            SignalEvent.topic_id == topic_id,
            SignalEvent.timestamp >= start_date
        ).count()

        return count

    except Exception:
        return 0


def _get_velocity_trend(db: Session, topic_id: str, days: int = 30) -> list[float]:
    """Get velocity trend for topic."""
    try:
        from datetime import date, timedelta

        start_date = date.today() - timedelta(days=days)

        features = db.query(TopicFeatures).filter(
            TopicFeatures.topic_id == topic_id,
            TopicFeatures.date >= start_date
        ).order_by(TopicFeatures.date.asc()).all()

        return [f.velocity for f in features]

    except Exception:
        return []


def _get_acceleration_trend(db: Session, topic_id: str, days: int = 30) -> list[float]:
    """Get acceleration trend for topic."""
    try:
        from datetime import date, timedelta

        start_date = date.today() - timedelta(days=days)

        features = db.query(TopicFeatures).filter(
            TopicFeatures.topic_id == topic_id,
            TopicFeatures.date >= start_date
        ).order_by(TopicFeatures.date.asc()).all()

        return [f.acceleration for f in features]

    except Exception:
        return []


def _get_contributing_sources(db: Session, topic_id: str, days: int = 30) -> Dict[str, int]:
    """Get contributing sources count for topic."""
    try:
        from datetime import datetime, timedelta

        start_date = datetime.utcnow() - timedelta(days=days)

        sources = {}
        for source in ["arxiv", "github", "jobs", "funding"]:
            count = db.query(SignalEvent).filter(
                SignalEvent.topic_id == topic_id,
                SignalEvent.source == source,
                SignalEvent.timestamp >= start_date
            ).count()

            sources[source] = count

        return sources

    except Exception:
        return {}
