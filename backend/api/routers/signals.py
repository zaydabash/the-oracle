"""Signals router for The Oracle."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from ...core.logging import get_logger
from ...db.session import get_db
from ...models.signal_event import SignalEvent
from ...schemas.signal_event import (
    SignalEventList,
    SignalEventResponse,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/signals", tags=["signals"])


@router.get("/", response_model=SignalEventList)
async def list_signal_events(
    topic_id: str | None = Query(None, description="Filter by topic ID"),
    source: str | None = Query(None, description="Filter by source"),
    start_date: datetime | None = Query(None, description="Start date filter"),
    end_date: datetime | None = Query(None, description="End date filter"),
    min_magnitude: float | None = Query(None, ge=0, description="Minimum magnitude filter"),
    limit: int = Query(100, ge=1, le=1000, description="Number of results to return"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    db: Session = Depends(get_db)
):
    """List signal events with optional filtering."""
    try:
        # Build query
        query = db.query(SignalEvent)

        # Apply filters
        filters = []

        if topic_id:
            filters.append(SignalEvent.topic_id == topic_id)

        if source:
            filters.append(SignalEvent.source == source)

        if start_date:
            filters.append(SignalEvent.timestamp >= start_date)

        if end_date:
            filters.append(SignalEvent.timestamp <= end_date)

        if min_magnitude is not None:
            filters.append(SignalEvent.magnitude >= min_magnitude)

        if filters:
            query = query.filter(and_(*filters))

        # Get total count
        total = query.count()

        # Apply pagination and ordering
        events = query.order_by(SignalEvent.timestamp.desc()).offset(offset).limit(limit).all()

        # Convert to response models
        event_responses = [SignalEventResponse.from_orm(event) for event in events]

        return SignalEventList(
            events=event_responses,
            total=total,
            limit=limit,
            offset=offset,
            has_more=(offset + limit) < total
        )

    except Exception as e:
        logger.error(f"Error listing signal events: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{event_id}", response_model=SignalEventResponse)
async def get_signal_event(
    event_id: str,
    db: Session = Depends(get_db)
):
    """Get a specific signal event by ID."""
    try:
        event = db.query(SignalEvent).filter(SignalEvent.id == event_id).first()

        if not event:
            raise HTTPException(status_code=404, detail="Signal event not found")

        return SignalEventResponse.from_orm(event)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting signal event {event_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/sources/stats")
async def get_source_statistics(
    days: int = Query(30, ge=1, le=365, description="Number of days to look back"),
    db: Session = Depends(get_db)
):
    """Get statistics by source."""
    try:
        from datetime import datetime, timedelta

        start_date = datetime.utcnow() - timedelta(days=days)

        # Get events by source
        sources = ["arxiv", "github", "jobs", "funding"]
        source_stats = {}

        for source in sources:
            events = db.query(SignalEvent).filter(
                SignalEvent.source == source,
                SignalEvent.timestamp >= start_date
            ).all()

            count = len(events)
            total_magnitude = sum(event.magnitude for event in events)
            avg_magnitude = total_magnitude / count if count > 0 else 0

            # Get unique topics
            topic_ids = set(event.topic_id for event in events if event.topic_id)

            source_stats[source] = {
                "event_count": count,
                "total_magnitude": total_magnitude,
                "avg_magnitude": avg_magnitude,
                "unique_topics": len(topic_ids),
                "topics": list(topic_ids)
            }

        return {
            "period_days": days,
            "sources": source_stats,
            "total_events": sum(stats["event_count"] for stats in source_stats.values()),
            "total_topics": len(set(
                topic_id for stats in source_stats.values()
                for topic_id in stats["topics"]
            ))
        }

    except Exception as e:
        logger.error(f"Error getting source statistics: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/recent/activity")
async def get_recent_activity(
    hours: int = Query(24, ge=1, le=168, description="Number of hours to look back"),
    limit: int = Query(50, ge=1, le=500, description="Number of recent events to return"),
    db: Session = Depends(get_db)
):
    """Get recent activity across all sources."""
    try:
        from datetime import datetime, timedelta

        start_time = datetime.utcnow() - timedelta(hours=hours)

        # Get recent events
        recent_events = db.query(SignalEvent).filter(
            SignalEvent.timestamp >= start_time
        ).order_by(SignalEvent.timestamp.desc()).limit(limit).all()

        # Group by time periods for activity timeline
        activity_timeline = {}
        for event in recent_events:
            # Round to hour for grouping
            hour_key = event.timestamp.replace(minute=0, second=0, microsecond=0)

            if hour_key not in activity_timeline:
                activity_timeline[hour_key] = {
                    "events": 0,
                    "sources": set(),
                    "topics": set(),
                    "total_magnitude": 0
                }

            activity_timeline[hour_key]["events"] += 1
            activity_timeline[hour_key]["sources"].add(event.source)
            if event.topic_id:
                activity_timeline[hour_key]["topics"].add(event.topic_id)
            activity_timeline[hour_key]["total_magnitude"] += event.magnitude

        # Convert sets to counts for JSON serialization
        timeline_data = []
        for hour, data in sorted(activity_timeline.items()):
            timeline_data.append({
                "hour": hour.isoformat(),
                "events": data["events"],
                "sources": len(data["sources"]),
                "topics": len(data["topics"]),
                "total_magnitude": data["total_magnitude"]
            })

        return {
            "period_hours": hours,
            "total_events": len(recent_events),
            "activity_timeline": timeline_data,
            "recent_events": [SignalEventResponse.from_orm(event) for event in recent_events]
        }

    except Exception as e:
        logger.error(f"Error getting recent activity: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/search")
async def search_signal_events(
    query: str = Query(..., min_length=1, description="Search query"),
    source: str | None = Query(None, description="Filter by source"),
    limit: int = Query(50, ge=1, le=200, description="Number of results to return"),
    db: Session = Depends(get_db)
):
    """Search signal events by title and description."""
    try:
        # Build search query
        search_filters = [
            or_(
                SignalEvent.title.ilike(f"%{query}%"),
                SignalEvent.description.ilike(f"%{query}%")
            )
        ]

        if source:
            search_filters.append(SignalEvent.source == source)

        # Execute search
        events = db.query(SignalEvent).filter(
            and_(*search_filters)
        ).order_by(SignalEvent.timestamp.desc()).limit(limit).all()

        return {
            "query": query,
            "results": [SignalEventResponse.from_orm(event) for event in events],
            "total_found": len(events)
        }

    except Exception as e:
        logger.error(f"Error searching signal events: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
