"""Surge ranking system for The Oracle."""

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from ..core.logging import get_logger
from ..db.session import get_db
from ..models.features import TopicFeatures
from ..models.forecast import TopicForecast
from ..models.topic import Topic

logger = get_logger(__name__)


class SurgeRanker:
    """
    Ranks topics by their predicted surge probability.
    
    The SurgeRanker uses a weighted scoring system to rank topics based on:
    - Surge score (40%): Primary predictive metric
    - Confidence (20%): Forecast reliability
    - Recent velocity (20%): Current momentum
    - Convergence (10%): Signal alignment across sources
    - Growth rate (10%): Historical trend strength
    
    The surge score itself is calculated using a sigmoid function over:
    - Velocity growth: Recent acceleration in signal volume
    - Z-spike: Statistical anomaly detection
    - Convergence: Cross-source signal alignment
    - Uncertainty penalty: Forecast confidence adjustment
    """

    def __init__(self):
        """Initialize the ranker with default weights."""
        self.ranking_weights = {
            "surge_score": 0.4,
            "confidence": 0.2,
            "recent_velocity": 0.2,
            "convergence": 0.1,
            "growth_rate": 0.1
        }

    def rank_topics(self, horizon_days: int = 30, limit: int = 20) -> list[dict]:
        """Rank topics by surge probability."""
        logger.info(f"Ranking topics by surge probability (horizon: {horizon_days}d)")

        with get_db() as db:
            # Get forecasts for the specified horizon
            forecasts = db.query(TopicForecast).filter(
                TopicForecast.horizon_days == horizon_days
            ).all()

            if not forecasts:
                logger.warning("No forecasts found for ranking")
                return []

            # Calculate ranking scores for each topic
            topic_scores = []

            for forecast in forecasts:
                try:
                    # Get topic information
                    topic = db.query(Topic).filter(
                        Topic.id == forecast.topic_id
                    ).first()

                    if not topic:
                        continue

                    # Get recent features for additional context
                    recent_features = self._get_recent_features(db, forecast.topic_id)

                    # Calculate composite ranking score
                    ranking_score = self._calculate_ranking_score(
                        forecast, recent_features
                    )

                    topic_scores.append({
                        "topic_id": topic.id,
                        "topic_name": topic.name,
                        "ranking_score": ranking_score,
                        "surge_score": forecast.surge_score,
                        "confidence": forecast.confidence_score,
                        "model_type": forecast.model_type,
                        "growth_rate": forecast.forecast_growth_rate,
                        "recent_velocity": recent_features.get("velocity", 0),
                        "recent_convergence": recent_features.get("convergence", 0),
                        "forecast_curve": forecast.forecast_curve
                    })

                except Exception as e:
                    logger.error(f"Error ranking topic {forecast.topic_id}: {e}")
                    continue

            # Sort by ranking score (descending)
            topic_scores.sort(key=lambda x: x["ranking_score"], reverse=True)

            # Add rank numbers
            for i, topic_data in enumerate(topic_scores[:limit]):
                topic_data["rank"] = i + 1

            logger.info(f"Ranked {len(topic_scores)} topics")
            return topic_scores[:limit]

    def _calculate_ranking_score(self, forecast: TopicForecast,
                               recent_features: dict) -> float:
        """Calculate composite ranking score for a topic."""
        try:
            # Base surge score
            surge_score = forecast.surge_score or 0

            # Confidence score
            confidence = forecast.confidence_score or 0

            # Recent velocity (normalized)
            recent_velocity = recent_features.get("velocity", 0)
            velocity_score = min(1.0, max(0, recent_velocity / 10.0))  # Normalize

            # Recent convergence
            recent_convergence = recent_features.get("convergence", 0)

            # Growth rate from forecast
            growth_rate = forecast.forecast_growth_rate or 0
            growth_score = min(1.0, max(0, growth_rate))  # Normalize

            # Calculate weighted composite score
            ranking_score = (
                self.ranking_weights["surge_score"] * surge_score +
                self.ranking_weights["confidence"] * confidence +
                self.ranking_weights["recent_velocity"] * velocity_score +
                self.ranking_weights["convergence"] * recent_convergence +
                self.ranking_weights["growth_rate"] * growth_score
            )

            # Apply bonus for high convergence
            if recent_convergence > 0.7:
                ranking_score *= 1.1

            # Apply penalty for very low confidence
            if confidence < 0.3:
                ranking_score *= 0.8

            return ranking_score

        except Exception as e:
            logger.error(f"Error calculating ranking score: {e}")
            return 0.0

    def _get_recent_features(self, db: Session, topic_id: str, days: int = 7) -> dict:
        """Get recent features for a topic."""
        try:
            start_date = datetime.utcnow().date() - timedelta(days=days)

            recent_features = db.query(TopicFeatures).filter(
                TopicFeatures.topic_id == topic_id,
                TopicFeatures.date >= start_date
            ).order_by(TopicFeatures.date.desc()).first()

            if recent_features:
                return {
                    "velocity": recent_features.velocity,
                    "acceleration": recent_features.acceleration,
                    "convergence": recent_features.convergence,
                    "z_spike": recent_features.z_spike,
                    "mention_count": recent_features.mention_count_total
                }
            else:
                return {}

        except Exception as e:
            logger.error(f"Error getting recent features for topic {topic_id}: {e}")
            return {}

    def get_topic_ranking_history(self, topic_id: str, days: int = 30) -> list[dict]:
        """Get ranking history for a topic."""
        with get_db() as db:
            # This would require storing historical rankings
            # For now, return empty list
            return []

    def get_ranking_insights(self, rankings: list[dict]) -> dict:
        """Generate insights from topic rankings."""
        if not rankings:
            return {}

        try:
            # Calculate statistics
            surge_scores = [r["surge_score"] for r in rankings]
            confidences = [r["confidence"] for r in rankings]

            insights = {
                "total_ranked": len(rankings),
                "avg_surge_score": sum(surge_scores) / len(surge_scores),
                "max_surge_score": max(surge_scores),
                "min_surge_score": min(surge_scores),
                "avg_confidence": sum(confidences) / len(confidences),
                "high_confidence_count": len([c for c in confidences if c > 0.7]),
                "top_topic": rankings[0]["topic_name"] if rankings else None,
                "model_distribution": self._get_model_distribution(rankings)
            }

            return insights

        except Exception as e:
            logger.error(f"Error generating ranking insights: {e}")
            return {}

    def _get_model_distribution(self, rankings: list[dict]) -> dict[str, int]:
        """Get distribution of models used in rankings."""
        model_counts = {}

        for ranking in rankings:
            model_type = ranking.get("model_type", "Unknown")
            model_counts[model_type] = model_counts.get(model_type, 0) + 1

        return model_counts

    def get_emerging_topics(self, days: int = 7, threshold: float = 0.6) -> list[dict]:
        """Identify emerging topics with high surge potential."""
        logger.info(f"Identifying emerging topics (threshold: {threshold})")

        # Get recent rankings
        recent_rankings = self.rank_topics(horizon_days=30, limit=50)

        emerging_topics = []

        for ranking in recent_rankings:
            if ranking["surge_score"] >= threshold:
                # Check if topic has been consistently high
                consistency_score = self._calculate_consistency_score(ranking["topic_id"])

                emerging_topics.append({
                    "topic_id": ranking["topic_id"],
                    "topic_name": ranking["topic_name"],
                    "surge_score": ranking["surge_score"],
                    "ranking_score": ranking["ranking_score"],
                    "consistency_score": consistency_score,
                    "growth_rate": ranking["growth_rate"],
                    "confidence": ranking["confidence"]
                })

        # Sort by combined score
        emerging_topics.sort(
            key=lambda x: x["surge_score"] * x["consistency_score"],
            reverse=True
        )

        logger.info(f"Identified {len(emerging_topics)} emerging topics")
        return emerging_topics

    def _calculate_consistency_score(self, topic_id: str) -> float:
        """Calculate consistency score for a topic."""
        # This would require historical ranking data
        # For now, return a default score
        return 0.8

    def get_ranking_alerts(self, rankings: list[dict]) -> list[dict]:
        """Generate alerts based on rankings."""
        alerts = []

        try:
            # Check for significant changes
            if rankings:
                top_topic = rankings[0]

                # High surge score alert
                if top_topic["surge_score"] > 0.8:
                    alerts.append({
                        "type": "high_surge",
                        "severity": "high",
                        "message": f"Topic '{top_topic['topic_name']}' has very high surge score: {top_topic['surge_score']:.2f}",
                        "topic_id": top_topic["topic_id"],
                        "value": top_topic["surge_score"]
                    })

                # Low confidence alert
                if top_topic["confidence"] < 0.4:
                    alerts.append({
                        "type": "low_confidence",
                        "severity": "medium",
                        "message": f"Topic '{top_topic['topic_name']}' has low forecast confidence: {top_topic['confidence']:.2f}",
                        "topic_id": top_topic["topic_id"],
                        "value": top_topic["confidence"]
                    })

                # High growth rate alert
                if top_topic["growth_rate"] and top_topic["growth_rate"] > 1.0:
                    alerts.append({
                        "type": "high_growth",
                        "severity": "high",
                        "message": f"Topic '{top_topic['topic_name']}' predicted to grow by {top_topic['growth_rate']:.1%}",
                        "topic_id": top_topic["topic_id"],
                        "value": top_topic["growth_rate"]
                    })

            return alerts

        except Exception as e:
            logger.error(f"Error generating ranking alerts: {e}")
            return []


def main():
    """Main function for running ranking from command line."""
    import typer

    app = typer.Typer()

    @app.command()
    def rank(horizon: int = 30, limit: int = 20):
        """Rank topics by surge probability."""
        ranker = SurgeRanker()
        rankings = ranker.rank_topics(horizon_days=horizon, limit=limit)

        print(f"Topic Rankings (Top {limit}):")
        for i, ranking in enumerate(rankings, 1):
            print(f"{i:2d}. {ranking['topic_name']}")
            print(f"    Surge Score: {ranking['surge_score']:.3f}")
            print(f"    Confidence:  {ranking['confidence']:.3f}")
            print(f"    Growth Rate: {ranking['growth_rate']:.1%}")
            print()

    @app.command()
    def emerging(threshold: float = 0.6):
        """Identify emerging topics."""
        ranker = SurgeRanker()
        emerging = ranker.get_emerging_topics(threshold=threshold)

        print(f"Emerging Topics (threshold: {threshold}):")
        for topic in emerging:
            print(f"- {topic['topic_name']}")
            print(f"  Surge Score: {topic['surge_score']:.3f}")
            print(f"  Growth Rate: {topic['growth_rate']:.1%}")
            print()

    @app.command()
    def insights():
        """Get ranking insights."""
        ranker = SurgeRanker()
        rankings = ranker.rank_topics(limit=20)
        insights = ranker.get_ranking_insights(rankings)

        print("Ranking Insights:")
        for key, value in insights.items():
            print(f"  {key}: {value}")

    app()


if __name__ == "__main__":
    main()
