"""Narrative generation for executive summaries."""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from jinja2 import Template

from ..core.logging import get_logger
from ..db.session import get_db
from ..models.topic import Topic
from ..models.signal_event import SignalEvent
from ..models.features import TopicFeatures
from ..models.forecast import TopicForecast
from ..forecasting.ranker import SurgeRanker

logger = get_logger(__name__)


class NarrativeGenerator:
    """Generates executive summaries and narratives from forecast data."""
    
    def __init__(self):
        self.ranker = SurgeRanker()
        self.templates = self._load_templates()
    
    def _load_templates(self) -> Dict[str, Template]:
        """Load narrative templates."""
        templates = {
            "topic_summary": Template("""
{% if surge_score >= 0.8 %}
**{{ topic_name }}** shows **exceptional momentum** with a {{ surge_score|round(2) }} surge score.
{% elif surge_score >= 0.6 %}
**{{ topic_name }}** demonstrates **strong growth potential** with a {{ surge_score|round(2) }} surge score.
{% elif surge_score >= 0.4 %}
**{{ topic_name }}** indicates **moderate interest** with a {{ surge_score|round(2) }} surge score.
{% else %}
**{{ topic_name }}** shows **limited momentum** with a {{ surge_score|round(2) }} surge score.
{% endif %}

{% if recent_velocity > 0 %}
Recent activity shows {{ velocity_change|round(1) }}% change in velocity over the past week.
{% endif %}

{% if convergence > 0.5 %}
Multiple data sources ({{ active_sources|length }}/4) indicate broad market interest.
{% endif %}

{% if forecast_growth_rate %}
**Forecast**: {{ growth_percentage }}% expected growth over next {{ horizon_days }} days.
{% endif %}
"""),
            
            "signal_breakdown": Template("""
**Contributing Signals** (last 30 days):
{% for source, data in sources.items() %}
- **{{ source|title }}**: {{ data.count }} events ({{ data.magnitude|round(1) }} magnitude)
{% endfor %}
"""),
            
            "executive_summary": Template("""
## Oracle Intelligence Report
*Generated: {{ timestamp }}*

### Top Trending Topics

{% for ranking in top_rankings[:5] %}
**{{ ranking.rank }}. {{ ranking.topic_name }}**
- Surge Score: {{ ranking.surge_score|round(2) }}
- Confidence: {{ ranking.confidence|round(2) }}
- Growth Rate: {{ ranking.growth_rate|round(1) }}%
{% endfor %}

### Key Insights

{% if insights.high_surge_topics > 0 %}
- {{ insights.high_surge_topics }} topics show exceptional momentum (surge > 0.8)
{% endif %}
{% if insights.high_confidence_count > 0 %}
- {{ insights.high_confidence_count }} forecasts have high confidence (>0.7)
{% endif %}
{% if insights.top_topic %}
- **{{ insights.top_topic }}** leads the rankings with strongest signal convergence
{% endif %}

### Alerts

{% for alert in alerts %}
- **{{ alert.type|title }}**: {{ alert.message }}
{% endfor %}
"""),
            
            "topic_detail": Template("""
# {{ topic_name }} - Forecast Analysis

## Current Status
- **Surge Score**: {{ surge_score|round(3) }}
- **Confidence**: {{ confidence|round(3) }}
- **Growth Rate**: {{ growth_rate|round(1) }}%
- **Model**: {{ model_type }}

## Recent Activity
- **Total Mentions** (30d): {{ recent_mentions }}
- **Velocity**: {{ current_velocity|round(2) }}
- **Acceleration**: {{ current_acceleration|round(2) }}
- **Convergence**: {{ convergence|round(2) }}

## Forecast Summary
{% for horizon, forecast in forecasts.items() %}
### {{ horizon }} Forecast
- **Growth**: {{ forecast.growth_rate|round(1) }}%
- **Confidence**: {{ forecast.confidence|round(2) }}
- **Model**: {{ forecast.model_type }}
{% endfor %}

## Signal Sources
{% for source, count in source_counts.items() %}
- **{{ source|title }}**: {{ count }} events
{% endfor %}

## Key Insights
{{ insights }}
""")
        }
        
        return templates
    
    def generate_topic_summary(self, topic_id: str, horizon_days: int = 30) -> str:
        """Generate summary narrative for a specific topic."""
        try:
            with get_db() as db:
                # Get topic information
                topic = db.query(Topic).filter(Topic.id == topic_id).first()
                if not topic:
                    return f"Topic {topic_id} not found."
                
                # Get forecast
                forecast = db.query(TopicForecast).filter(
                    TopicForecast.topic_id == topic_id,
                    TopicForecast.horizon_days == horizon_days
                ).first()
                
                if not forecast:
                    return f"No forecast available for topic {topic.name}."
                
                # Get recent features
                recent_features = self._get_recent_features(db, topic_id)
                
                # Get source breakdown
                source_breakdown = self._get_source_breakdown(db, topic_id)
                
                # Calculate metrics
                velocity_change = self._calculate_velocity_change(db, topic_id)
                
                # Generate narrative
                context = {
                    "topic_name": topic.name,
                    "surge_score": forecast.surge_score,
                    "confidence": forecast.confidence_score,
                    "recent_velocity": recent_features.get("velocity", 0),
                    "velocity_change": velocity_change,
                    "convergence": recent_features.get("convergence", 0),
                    "active_sources": [s for s, data in source_breakdown.items() if data["count"] > 0],
                    "forecast_growth_rate": forecast.forecast_growth_rate,
                    "growth_percentage": (forecast.forecast_growth_rate * 100) if forecast.forecast_growth_rate else 0,
                    "horizon_days": horizon_days,
                    "sources": source_breakdown
                }
                
                narrative = self.templates["topic_summary"].render(**context)
                
                # Add signal breakdown
                signal_breakdown = self.templates["signal_breakdown"].render(**context)
                
                return narrative + "\n\n" + signal_breakdown
                
        except Exception as e:
            logger.error(f"Error generating topic summary for {topic_id}: {e}")
            return f"Error generating summary: {str(e)}"
    
    def generate_executive_summary(self, limit: int = 10) -> str:
        """Generate executive summary report."""
        try:
            # Get top rankings
            rankings = self.ranker.rank_topics(horizon_days=30, limit=limit)
            
            if not rankings:
                return "No forecast data available for executive summary."
            
            # Get insights
            insights = self.ranker.get_ranking_insights(rankings)
            
            # Get alerts
            alerts = self.ranker.get_ranking_alerts(rankings)
            
            # Generate context
            context = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M UTC"),
                "top_rankings": rankings,
                "insights": {
                    "high_surge_topics": len([r for r in rankings if r["surge_score"] > 0.8]),
                    "high_confidence_count": len([r for r in rankings if r["confidence"] > 0.7]),
                    "top_topic": rankings[0]["topic_name"] if rankings else None
                },
                "alerts": alerts
            }
            
            narrative = self.templates["executive_summary"].render(**context)
            return narrative
            
        except Exception as e:
            logger.error(f"Error generating executive summary: {e}")
            return f"Error generating executive summary: {str(e)}"
    
    def generate_topic_detail_report(self, topic_id: str) -> str:
        """Generate detailed report for a topic."""
        try:
            with get_db() as db:
                # Get topic information
                topic = db.query(Topic).filter(Topic.id == topic_id).first()
                if not topic:
                    return f"Topic {topic_id} not found."
                
                # Get all forecasts for different horizons
                forecasts = {}
                for horizon in [30, 90, 180]:
                    forecast = db.query(TopicForecast).filter(
                        TopicForecast.topic_id == topic_id,
                        TopicForecast.horizon_days == horizon
                    ).first()
                    
                    if forecast:
                        forecasts[f"{horizon} days"] = {
                            "growth_rate": forecast.forecast_growth_rate,
                            "confidence": forecast.confidence_score,
                            "model_type": forecast.model_type
                        }
                
                if not forecasts:
                    return f"No forecast data available for topic {topic.name}."
                
                # Get recent features
                recent_features = self._get_recent_features(db, topic_id)
                
                # Get source counts
                source_counts = self._get_source_counts(db, topic_id)
                
                # Get recent mentions count
                recent_mentions = self._get_recent_mentions(db, topic_id, days=30)
                
                # Get primary forecast for main metrics
                primary_forecast = db.query(TopicForecast).filter(
                    TopicForecast.topic_id == topic_id,
                    TopicForecast.horizon_days == 30
                ).first()
                
                # Generate insights
                insights = self._generate_topic_insights(topic_id, recent_features, forecasts)
                
                # Generate context
                context = {
                    "topic_name": topic.name,
                    "surge_score": primary_forecast.surge_score if primary_forecast else 0,
                    "confidence": primary_forecast.confidence_score if primary_forecast else 0,
                    "growth_rate": primary_forecast.forecast_growth_rate if primary_forecast else 0,
                    "model_type": primary_forecast.model_type if primary_forecast else "Unknown",
                    "recent_mentions": recent_mentions,
                    "current_velocity": recent_features.get("velocity", 0),
                    "current_acceleration": recent_features.get("acceleration", 0),
                    "convergence": recent_features.get("convergence", 0),
                    "forecasts": forecasts,
                    "source_counts": source_counts,
                    "insights": insights
                }
                
                narrative = self.templates["topic_detail"].render(**context)
                return narrative
                
        except Exception as e:
            logger.error(f"Error generating topic detail report for {topic_id}: {e}")
            return f"Error generating detail report: {str(e)}"
    
    def _get_recent_features(self, db, topic_id: str, days: int = 7) -> Dict:
        """Get recent features for a topic."""
        try:
            start_date = datetime.now().date() - timedelta(days=days)
            
            recent_feature = db.query(TopicFeatures).filter(
                TopicFeatures.topic_id == topic_id,
                TopicFeatures.date >= start_date
            ).order_by(TopicFeatures.date.desc()).first()
            
            if recent_feature:
                return {
                    "velocity": recent_feature.velocity,
                    "acceleration": recent_feature.acceleration,
                    "convergence": recent_feature.convergence,
                    "z_spike": recent_feature.z_spike
                }
            else:
                return {}
                
        except Exception as e:
            logger.error(f"Error getting recent features: {e}")
            return {}
    
    def _get_source_breakdown(self, db, topic_id: str, days: int = 30) -> Dict:
        """Get breakdown of events by source."""
        try:
            start_date = datetime.now() - timedelta(days=days)
            
            # Get events by source
            events_by_source = {}
            for source in ["arxiv", "github", "jobs", "funding"]:
                events = db.query(SignalEvent).filter(
                    SignalEvent.topic_id == topic_id,
                    SignalEvent.source == source,
                    SignalEvent.timestamp >= start_date
                ).all()
                
                count = len(events)
                magnitude = sum(event.magnitude for event in events)
                
                events_by_source[source] = {
                    "count": count,
                    "magnitude": magnitude
                }
            
            return events_by_source
            
        except Exception as e:
            logger.error(f"Error getting source breakdown: {e}")
            return {}
    
    def _get_source_counts(self, db, topic_id: str, days: int = 30) -> Dict[str, int]:
        """Get simple source counts."""
        try:
            start_date = datetime.now() - timedelta(days=days)
            
            source_counts = {}
            for source in ["arxiv", "github", "jobs", "funding"]:
                count = db.query(SignalEvent).filter(
                    SignalEvent.topic_id == topic_id,
                    SignalEvent.source == source,
                    SignalEvent.timestamp >= start_date
                ).count()
                
                source_counts[source] = count
            
            return source_counts
            
        except Exception as e:
            logger.error(f"Error getting source counts: {e}")
            return {}
    
    def _get_recent_mentions(self, db, topic_id: str, days: int = 30) -> int:
        """Get recent mention count."""
        try:
            start_date = datetime.now() - timedelta(days=days)
            
            count = db.query(SignalEvent).filter(
                SignalEvent.topic_id == topic_id,
                SignalEvent.timestamp >= start_date
            ).count()
            
            return count
            
        except Exception as e:
            logger.error(f"Error getting recent mentions: {e}")
            return 0
    
    def _calculate_velocity_change(self, db, topic_id: str, days: int = 7) -> float:
        """Calculate velocity change over time."""
        try:
            start_date = datetime.now().date() - timedelta(days=days)
            
            features = db.query(TopicFeatures).filter(
                TopicFeatures.topic_id == topic_id,
                TopicFeatures.date >= start_date
            ).order_by(TopicFeatures.date.asc()).all()
            
            if len(features) < 2:
                return 0.0
            
            # Calculate percentage change in velocity
            first_velocity = features[0].velocity
            last_velocity = features[-1].velocity
            
            if first_velocity == 0:
                return 100.0 if last_velocity > 0 else 0.0
            
            change = ((last_velocity - first_velocity) / first_velocity) * 100
            return change
            
        except Exception as e:
            logger.error(f"Error calculating velocity change: {e}")
            return 0.0
    
    def _generate_topic_insights(self, topic_id: str, recent_features: Dict, 
                               forecasts: Dict) -> str:
        """Generate insights for a topic."""
        insights = []
        
        try:
            # Velocity insights
            velocity = recent_features.get("velocity", 0)
            if velocity > 5:
                insights.append("High activity velocity indicates strong momentum.")
            elif velocity > 2:
                insights.append("Moderate velocity suggests steady interest.")
            else:
                insights.append("Low velocity indicates limited recent activity.")
            
            # Convergence insights
            convergence = recent_features.get("convergence", 0)
            if convergence > 0.7:
                insights.append("High source convergence suggests broad market validation.")
            elif convergence > 0.4:
                insights.append("Moderate convergence indicates growing interest across channels.")
            
            # Growth insights
            if forecasts:
                max_growth = max(f.get("growth_rate", 0) for f in forecasts.values())
                if max_growth > 0.5:
                    insights.append(f"Strong growth potential with up to {max_growth:.1%} projected growth.")
                elif max_growth > 0.2:
                    insights.append(f"Moderate growth expected with {max_growth:.1%} projected growth.")
            
            return " ".join(insights) if insights else "Limited insights available."
            
        except Exception as e:
            logger.error(f"Error generating insights: {e}")
            return "Error generating insights."
    
    def export_weekly_digest(self, output_path: str = None) -> str:
        """Export weekly digest report."""
        try:
            # Generate executive summary
            digest = self.generate_executive_summary(limit=20)
            
            # Add emerging topics section
            emerging_topics = self.ranker.get_emerging_topics(threshold=0.6)
            
            if emerging_topics:
                digest += "\n\n## Emerging Topics\n\n"
                for topic in emerging_topics[:5]:
                    digest += f"**{topic['topic_name']}**\n"
                    digest += f"- Surge Score: {topic['surge_score']:.3f}\n"
                    digest += f"- Growth Rate: {topic['growth_rate']:.1%}\n\n"
            
            # Add timestamp
            digest += f"\n---\n*Report generated: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}*\n"
            
            # Save to file if path provided
            if output_path:
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(digest)
                logger.info(f"Weekly digest saved to {output_path}")
            
            return digest
            
        except Exception as e:
            logger.error(f"Error generating weekly digest: {e}")
            return f"Error generating digest: {str(e)}"


def main():
    """Main function for running narrative generation from command line."""
    import typer
    
    app = typer.Typer()
    
    @app.command()
    def summary(topic_id: str, horizon: int = 30):
        """Generate topic summary."""
        generator = NarrativeGenerator()
        narrative = generator.generate_topic_summary(topic_id, horizon)
        print(narrative)
    
    @app.command()
    def executive():
        """Generate executive summary."""
        generator = NarrativeGenerator()
        narrative = generator.generate_executive_summary()
        print(narrative)
    
    @app.command()
    def detail(topic_id: str):
        """Generate topic detail report."""
        generator = NarrativeGenerator()
        narrative = generator.generate_topic_detail_report(topic_id)
        print(narrative)
    
    @app.command()
    def digest(output_file: str = None):
        """Generate weekly digest."""
        generator = NarrativeGenerator()
        digest = generator.export_weekly_digest(output_file)
        
        if not output_file:
            print(digest)
        else:
            print(f"Digest saved to {output_file}")
    
    app()


if __name__ == "__main__":
    main()
