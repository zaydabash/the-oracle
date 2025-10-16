"""Feature matrix builder for The Oracle."""

import uuid
from datetime import date, timedelta

from sqlalchemy.orm import Session

from ..core.logging import get_logger
from ..db.session import get_db
from ..models.features import TopicFeatures
from ..models.signal_event import SignalEvent
from ..models.topic import Topic
from .timeseries import TimeSeriesAnalyzer
from .topic_mapping import TopicMapper

logger = get_logger(__name__)


class FeatureMatrixBuilder:
    """Builds feature matrix from signal events."""

    def __init__(self, window_size: int = 7, alpha: float = 0.3):
        self.ts_analyzer = TimeSeriesAnalyzer(window_size, alpha)
        self.topic_mapper = TopicMapper()

    def build_feature_matrix(self, days: int = 90, force_rebuild: bool = False) -> dict[str, int]:
        """Build feature matrix for all topics."""
        logger.info(f"Building feature matrix for last {days} days")

        results = {}

        with get_db() as db:
            # Get all topics
            topics = db.query(Topic).all()

            for topic in topics:
                try:
                    count = self._build_topic_features(db, topic.id, days, force_rebuild)
                    results[topic.name] = count
                    logger.info(f"Built {count} feature records for topic: {topic.name}")
                except Exception as e:
                    logger.error(f"Error building features for topic {topic.name}: {e}")
                    results[topic.name] = 0

        total_features = sum(results.values())
        logger.info(f"Feature matrix build completed. Total features: {total_features}")

        return results

    def _build_topic_features(self, db: Session, topic_id: str, days: int,
                            force_rebuild: bool) -> int:
        """Build features for a specific topic."""
        start_date = date.today() - timedelta(days=days)

        # Get existing features for this topic
        existing_features = db.query(TopicFeatures).filter(
            TopicFeatures.topic_id == topic_id,
            TopicFeatures.date >= start_date
        ).all()

        if existing_features and not force_rebuild:
            logger.info(f"Features already exist for topic {topic_id}, skipping")
            return len(existing_features)

        # Get events for this topic
        events = db.query(SignalEvent).filter(
            SignalEvent.topic_id == topic_id,
            SignalEvent.timestamp >= start_date
        ).order_by(SignalEvent.timestamp.asc()).all()

        if not events:
            logger.warning(f"No events found for topic {topic_id}")
            return 0

        # Group events by date and source
        daily_events = {}
        for event in events:
            event_date = event.timestamp.date()
            if event_date not in daily_events:
                daily_events[event_date] = {}
            if event.source not in daily_events[event_date]:
                daily_events[event_date][event.source] = []
            daily_events[event_date][event.source].append(event)

        # Build features for each date
        feature_records = []
        dates = sorted(daily_events.keys())

        for i, current_date in enumerate(dates):
            # Get events for current date
            current_events = daily_events[current_date]

            # Calculate daily metrics
            daily_metrics = self._calculate_daily_metrics(current_events)

            # Calculate time series features
            ts_features = self._calculate_timeseries_features(
                dates[:i+1], daily_events, current_date
            )

            # Create feature record
            feature_record = TopicFeatures(
                id=str(uuid.uuid4()),
                topic_id=topic_id,
                date=current_date,
                **daily_metrics,
                **ts_features
            )

            feature_records.append(feature_record)

        # Store features in database
        if force_rebuild and existing_features:
            # Delete existing features
            for feature in existing_features:
                db.delete(feature)

        # Add new features
        for feature in feature_records:
            db.add(feature)

        try:
            db.commit()
            logger.info(f"Stored {len(feature_records)} feature records for topic {topic_id}")
        except Exception as e:
            logger.error(f"Error storing features for topic {topic_id}: {e}")
            db.rollback()
            raise

        return len(feature_records)

    def _calculate_daily_metrics(self, daily_events: dict[str, list[SignalEvent]]) -> dict:
        """Calculate daily metrics for a topic."""
        metrics = {
            "mention_count_total": 0,
            "mention_count_arxiv": 0,
            "mention_count_github": 0,
            "mention_count_jobs": 0,
            "mention_count_funding": 0,
            "magnitude_sum": 0.0,
            "unique_sources": 0
        }

        sources = set()

        for source, events in daily_events.items():
            count = len(events)
            magnitude_sum = sum(event.magnitude for event in events)

            metrics["mention_count_total"] += count
            metrics["magnitude_sum"] += magnitude_sum
            sources.add(source)

            # Source-specific counts
            if source == "arxiv":
                metrics["mention_count_arxiv"] = count
            elif source == "github":
                metrics["mention_count_github"] = count
            elif source == "jobs":
                metrics["mention_count_jobs"] = count
            elif source == "funding":
                metrics["mention_count_funding"] = count

        metrics["unique_sources"] = len(sources)

        return metrics

    def _calculate_timeseries_features(self, dates: list[date],
                                     daily_events: dict[date, dict[str, list[SignalEvent]]],
                                     current_date: date) -> dict:
        """Calculate time series features up to current date."""
        if len(dates) < 2:
            return {
                "velocity": 0.0,
                "acceleration": 0.0,
                "z_spike": 0.0,
                "convergence": 0.0
            }

        # Get values up to current date
        values = []
        source_counts = {
            "arxiv": [],
            "github": [],
            "jobs": [],
            "funding": []
        }

        for date_val in dates:
            if date_val in daily_events:
                events = daily_events[date_val]
                daily_value = sum(
                    sum(event.magnitude for event in source_events)
                    for source_events in events.values()
                )
                values.append(daily_value)

                # Source-specific counts
                for source in source_counts.keys():
                    count = len(events.get(source, []))
                    source_counts[source].append(count)
            else:
                values.append(0.0)
                for source in source_counts.keys():
                    source_counts[source].append(0)

        # Calculate time series features
        velocity = self.ts_analyzer.calculate_velocity(values)
        acceleration = self.ts_analyzer.calculate_acceleration(velocity)
        z_spikes = self.ts_analyzer.calculate_z_score_spike(values)
        convergence = self.ts_analyzer.calculate_convergence(source_counts)

        return {
            "velocity": velocity[-1] if velocity else 0.0,
            "acceleration": acceleration[-1] if acceleration else 0.0,
            "z_spike": z_spikes[-1] if z_spikes else 0.0,
            "convergence": convergence[-1] if convergence else 0.0
        }

    def rebuild_topic_features(self, topic_id: str, days: int = 90) -> int:
        """Rebuild features for a specific topic."""
        with get_db() as db:
            return self._build_topic_features(db, topic_id, days, force_rebuild=True)

    def get_feature_summary(self, topic_id: str, days: int = 30) -> dict:
        """Get feature summary for a topic."""
        with get_db() as db:
            start_date = date.today() - timedelta(days=days)

            features = db.query(TopicFeatures).filter(
                TopicFeatures.topic_id == topic_id,
                TopicFeatures.date >= start_date
            ).order_by(TopicFeatures.date.asc()).all()

            if not features:
                return {}

            # Calculate summary statistics
            total_mentions = sum(f.mention_count_total for f in features)
            avg_velocity = sum(f.velocity for f in features) / len(features)
            avg_acceleration = sum(f.acceleration for f in features) / len(features)
            max_z_spike = max(f.z_spike for f in features)
            avg_convergence = sum(f.convergence for f in features) / len(features)

            return {
                "total_mentions": total_mentions,
                "avg_velocity": avg_velocity,
                "avg_acceleration": avg_acceleration,
                "max_z_spike": max_z_spike,
                "avg_convergence": avg_convergence,
                "feature_count": len(features),
                "date_range": {
                    "start": features[0].date.isoformat(),
                    "end": features[-1].date.isoformat()
                }
            }

    def cleanup_old_features(self, days: int = 180) -> int:
        """Clean up old feature records."""
        cutoff_date = date.today() - timedelta(days=days)

        with get_db() as db:
            try:
                old_features = db.query(TopicFeatures).filter(
                    TopicFeatures.date < cutoff_date
                )

                count = old_features.count()
                old_features.delete(synchronize_session=False)
                db.commit()

                logger.info(f"Cleaned up {count} old feature records")
                return count

            except Exception as e:
                logger.error(f"Error cleaning up old features: {e}")
                db.rollback()
                raise


def main():
    """Main function for running feature matrix builder from command line."""
    import typer

    app = typer.Typer()

    @app.command()
    def build(days: int = 90, force: bool = False):
        """Build feature matrix."""
        builder = FeatureMatrixBuilder()
        results = builder.build_feature_matrix(days=days, force_rebuild=force)

        print("Feature Matrix Build Results:")
        for topic, count in results.items():
            print(f"  {topic}: {count} features")
        print(f"Total: {sum(results.values())} features")

    @app.command()
    def rebuild_topic(topic_id: str, days: int = 90):
        """Rebuild features for specific topic."""
        builder = FeatureMatrixBuilder()
        count = builder.rebuild_topic_features(topic_id, days=days)
        print(f"Rebuilt {count} features for topic {topic_id}")

    @app.command()
    def summary(topic_id: str, days: int = 30):
        """Get feature summary for topic."""
        builder = FeatureMatrixBuilder()
        summary_data = builder.get_feature_summary(topic_id, days=days)

        print(f"Feature Summary for {topic_id} (last {days} days):")
        for key, value in summary_data.items():
            print(f"  {key}: {value}")

    @app.command()
    def cleanup(days: int = 180):
        """Clean up old features."""
        builder = FeatureMatrixBuilder()
        count = builder.cleanup_old_features(days=days)
        print(f"Cleaned up {count} old feature records")

    app()


if __name__ == "__main__":
    main()
