"""Health check router for The Oracle."""

from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ...core.logging import get_logger
from ...db.session import get_db
from ...models.signal_event import SignalEvent
from ...models.topic import Topic
from ...models.forecast import TopicForecast

logger = get_logger(__name__)

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/")
async def health_check(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Basic health check endpoint."""
    try:
        # Check database connection
        db.execute("SELECT 1")
        
        # Get basic statistics
        total_events = db.query(SignalEvent).count()
        total_topics = db.query(Topic).count()
        total_forecasts = db.query(TopicForecast).count()
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "database": "connected",
            "statistics": {
                "total_events": total_events,
                "total_topics": total_topics,
                "total_forecasts": total_forecasts
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "database": "disconnected",
            "error": str(e)
        }


@router.get("/ready")
async def readiness_check(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Readiness check endpoint."""
    try:
        # Check if we have basic data
        topics_count = db.query(Topic).count()
        events_count = db.query(SignalEvent).count()
        
        if topics_count == 0:
            return {
                "status": "not_ready",
                "reason": "no_topics_configured",
                "timestamp": datetime.utcnow().isoformat()
            }
        
        if events_count == 0:
            return {
                "status": "not_ready",
                "reason": "no_events_available",
                "timestamp": datetime.utcnow().isoformat()
            }
        
        return {
            "status": "ready",
            "timestamp": datetime.utcnow().isoformat(),
            "topics_count": topics_count,
            "events_count": events_count
        }
        
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return {
            "status": "not_ready",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }
