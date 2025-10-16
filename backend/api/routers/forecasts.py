"""Forecasts router for The Oracle."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ...core.logging import get_logger
from ...db.session import get_db
from ...models.forecast import TopicForecast
from ...models.topic import Topic
from ...schemas.forecast import ForecastSummary, ForecastLeaderboard, TopicForecastDetail
from ...forecasting.ranker import SurgeRanker
from ...forecasting.baseline import BaselineForecaster

logger = get_logger(__name__)

router = APIRouter(prefix="/forecasts", tags=["forecasts"])


@router.get("/leaderboard", response_model=ForecastLeaderboard)
async def get_forecast_leaderboard(
    horizon: int = Query(30, ge=1, le=365, description="Forecast horizon in days"),
    limit: int = Query(20, ge=1, le=100, description="Number of topics to return"),
    db: Session = Depends(get_db)
):
    """Get forecast leaderboard ranked by surge probability."""
    try:
        ranker = SurgeRanker()
        rankings = ranker.rank_topics(horizon_days=horizon, limit=limit)
        
        if not rankings:
            return ForecastLeaderboard(
                forecasts=[],
                total=0,
                generated_at=datetime.utcnow()
            )
        
        # Convert rankings to forecast summaries
        forecasts = []
        for ranking in rankings:
            forecast_summary = ForecastSummary(
                topic_id=ranking["topic_id"],
                topic_name=ranking["topic_name"],
                horizon_30d=ranking["surge_score"] if horizon == 30 else None,
                horizon_90d=None,  # Could be extended to get multiple horizons
                horizon_180d=None,
                surge_score=ranking["surge_score"],
                confidence=ranking["confidence"],
                growth_rate=ranking["growth_rate"]
            )
            forecasts.append(forecast_summary)
        
        return ForecastLeaderboard(
            forecasts=forecasts,
            total=len(forecasts),
            generated_at=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Error getting forecast leaderboard: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/topic/{topic_id}", response_model=TopicForecastDetail)
async def get_topic_forecast_detail(
    topic_id: str,
    horizon: int = Query(30, ge=1, le=365, description="Forecast horizon in days"),
    db: Session = Depends(get_db)
):
    """Get detailed forecast information for a specific topic."""
    try:
        # Check if topic exists
        topic = db.query(Topic).filter(Topic.id == topic_id).first()
        if not topic:
            raise HTTPException(status_code=404, detail="Topic not found")
        
        # Get forecast
        forecast = db.query(TopicForecast).filter(
            TopicForecast.topic_id == topic_id,
            TopicForecast.horizon_days == horizon
        ).first()
        
        if not forecast:
            raise HTTPException(status_code=404, detail="Forecast not found")
        
        # Get additional forecast data for different horizons
        all_forecasts = db.query(TopicForecast).filter(
            TopicForecast.topic_id == topic_id
        ).all()
        
        forecast_curves = {}
        for f in all_forecasts:
            forecast_curves[f.horizon_days] = f.forecast_curve
        
        # Get recent velocity trend
        velocity_trend = _get_velocity_trend(db, topic_id, days=30)
        
        # Get latest velocity
        latest_velocity = velocity_trend[-1] if velocity_trend else None
        
        # Build topic forecast detail
        forecast_detail = TopicForecastDetail(
            **forecast.to_dict(),
            topic_name=topic.name,
            latest_velocity=latest_velocity,
            velocity_trend=velocity_trend,
            forecast_growth_rate=forecast.forecast_growth_rate,
            model_performance=forecast.model_metrics
        )
        
        return forecast_detail
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting topic forecast detail for {topic_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/summary/{topic_id}")
async def get_topic_forecast_summary(
    topic_id: str,
    db: Session = Depends(get_db)
):
    """Get forecast summary for a topic across all horizons."""
    try:
        # Check if topic exists
        topic = db.query(Topic).filter(Topic.id == topic_id).first()
        if not topic:
            raise HTTPException(status_code=404, detail="Topic not found")
        
        # Get all forecasts for the topic
        forecasts = db.query(TopicForecast).filter(
            TopicForecast.topic_id == topic_id
        ).all()
        
        if not forecasts:
            return {
                "topic_id": topic_id,
                "topic_name": topic.name,
                "forecasts": {},
                "message": "No forecasts available"
            }
        
        # Build summary
        summary = {}
        for forecast in forecasts:
            horizon_key = f"horizon_{forecast.horizon_days}d"
            summary[horizon_key] = {
                "surge_score": forecast.surge_score,
                "confidence": forecast.confidence_score,
                "model_type": forecast.model_type,
                "growth_rate": forecast.forecast_growth_rate,
                "updated_at": forecast.updated_at.isoformat()
            }
        
        return {
            "topic_id": topic_id,
            "topic_name": topic.name,
            "forecasts": summary,
            "total_forecasts": len(forecasts)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting forecast summary for {topic_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/generate")
async def generate_forecasts(
    topic_id: Optional[str] = None,
    horizon: int = Query(30, ge=1, le=365, description="Forecast horizon in days"),
    force_rebuild: bool = Query(False, description="Force rebuild existing forecasts"),
    db: Session = Depends(get_db)
):
    """Generate forecasts for topics."""
    try:
        forecaster = BaselineForecaster()
        
        if topic_id:
            # Generate forecast for specific topic
            count = forecaster._forecast_topic_horizon(db, topic_id, horizon, force_rebuild)
            
            return {
                "message": f"Generated {count} forecast(s) for topic {topic_id}",
                "topic_id": topic_id,
                "horizon_days": horizon,
                "forecasts_generated": count
            }
        else:
            # Generate forecasts for all topics
            results = forecaster.forecast_all_topics(force_rebuild=force_rebuild)
            
            total_forecasts = sum(
                sum(topic_results.values()) if isinstance(topic_results, dict) else 0
                for topic_results in results.values()
                if isinstance(topic_results, dict) and "error" not in topic_results
            )
            
            return {
                "message": f"Generated {total_forecasts} forecasts for all topics",
                "results": results,
                "total_forecasts": total_forecasts
            }
        
    except Exception as e:
        logger.error(f"Error generating forecasts: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/insights")
async def get_forecast_insights(
    horizon: int = Query(30, ge=1, le=365, description="Forecast horizon in days"),
    db: Session = Depends(get_db)
):
    """Get insights from forecast data."""
    try:
        ranker = SurgeRanker()
        rankings = ranker.rank_topics(horizon_days=horizon, limit=50)
        
        if not rankings:
            return {"message": "No forecast data available for insights"}
        
        # Get insights from ranker
        insights = ranker.get_ranking_insights(rankings)
        
        # Get alerts
        alerts = ranker.get_ranking_alerts(rankings)
        
        # Get emerging topics
        emerging_topics = ranker.get_emerging_topics(threshold=0.6)
        
        return {
            "horizon_days": horizon,
            "insights": insights,
            "alerts": alerts,
            "emerging_topics": emerging_topics[:10],  # Top 10 emerging topics
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting forecast insights: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/models/performance")
async def get_model_performance(
    db: Session = Depends(get_db)
):
    """Get performance statistics for different forecasting models."""
    try:
        # Get all forecasts
        forecasts = db.query(TopicForecast).all()
        
        if not forecasts:
            return {"message": "No forecast data available"}
        
        # Group by model type
        model_stats = {}
        
        for forecast in forecasts:
            model_type = forecast.model_type or "Unknown"
            
            if model_type not in model_stats:
                model_stats[model_type] = {
                    "count": 0,
                    "avg_confidence": 0,
                    "avg_surge_score": 0,
                    "confidences": [],
                    "surge_scores": []
                }
            
            stats = model_stats[model_type]
            stats["count"] += 1
            stats["confidences"].append(forecast.confidence_score or 0)
            stats["surge_scores"].append(forecast.surge_score or 0)
        
        # Calculate averages
        for model_type, stats in model_stats.items():
            if stats["confidences"]:
                stats["avg_confidence"] = sum(stats["confidences"]) / len(stats["confidences"])
            if stats["surge_scores"]:
                stats["avg_surge_score"] = sum(stats["surge_scores"]) / len(stats["surge_scores"])
            
            # Remove raw lists for cleaner output
            del stats["confidences"]
            del stats["surge_scores"]
        
        return {
            "model_performance": model_stats,
            "total_forecasts": len(forecasts),
            "unique_models": len(model_stats)
        }
        
    except Exception as e:
        logger.error(f"Error getting model performance: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


def _get_velocity_trend(db: Session, topic_id: str, days: int = 30) -> List[float]:
    """Get velocity trend for topic."""
    try:
        from datetime import date, timedelta
        
        start_date = date.today() - timedelta(days=days)
        
        from ...models.features import TopicFeatures
        
        features = db.query(TopicFeatures).filter(
            TopicFeatures.topic_id == topic_id,
            TopicFeatures.date >= start_date
        ).order_by(TopicFeatures.date.asc()).all()
        
        return [f.velocity for f in features]
        
    except Exception:
        return []
