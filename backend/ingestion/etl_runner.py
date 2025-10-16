"""ETL runner for data ingestion pipeline."""

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from ..core.config import settings
from ..core.logging import get_logger
from ..db.session import get_db
from ..models.signal_event import SignalEvent
from .arxiv_client import ArxivClient
from .crunchbase_client import CrunchbaseClient
from .github_client import GitHubClient
from .jobs_client import JobsClient
from .normalizers import SignalEventNormalizer

logger = get_logger(__name__)


class ETLRunner:
    """ETL runner for orchestrating data ingestion."""

    def __init__(self):
        self.arxiv_client = ArxivClient()
        self.github_client = GitHubClient()
        self.jobs_client = JobsClient()
        self.crunchbase_client = CrunchbaseClient()
        self.normalizer = SignalEventNormalizer()

    def run_full_etl(self, days: int = 7) -> dict[str, int]:
        """Run full ETL pipeline for all sources."""
        logger.info(f"Starting full ETL pipeline for last {days} days")

        results = {}

        try:
            # Fetch data from all sources
            arxiv_papers = self.arxiv_client.fetch_recent_papers(days=days)
            github_repos = self.github_client.fetch_trending_repos(days=days)
            job_postings = self.jobs_client.fetch_recent_jobs(days=days)
            funding_rounds = self.crunchbase_client.fetch_recent_funding(days=days)

            # Normalize and store data
            with get_db() as db:
                results["arxiv"] = self._process_source_data(db, arxiv_papers, "arxiv")
                results["github"] = self._process_source_data(db, github_repos, "github")
                results["jobs"] = self._process_source_data(db, job_postings, "jobs")
                results["funding"] = self._process_source_data(db, funding_rounds, "funding")

            total_events = sum(results.values())
            logger.info(f"ETL completed successfully. Total events processed: {total_events}")

        except Exception as e:
            logger.error(f"Error in ETL pipeline: {e}")
            raise

        return results

    def run_source_etl(self, source: str, days: int = 7) -> int:
        """Run ETL for a specific source."""
        logger.info(f"Starting ETL for source: {source}")

        try:
            # Fetch data based on source
            if source == "arxiv":
                data = self.arxiv_client.fetch_recent_papers(days=days)
            elif source == "github":
                data = self.github_client.fetch_trending_repos(days=days)
            elif source == "jobs":
                data = self.jobs_client.fetch_recent_jobs(days=days)
            elif source == "funding":
                data = self.crunchbase_client.fetch_recent_funding(days=days)
            else:
                raise ValueError(f"Unknown source: {source}")

            # Process and store data
            with get_db() as db:
                processed_count = self._process_source_data(db, data, source)

            logger.info(f"ETL completed for {source}. Events processed: {processed_count}")
            return processed_count

        except Exception as e:
            logger.error(f"Error in ETL for source {source}: {e}")
            raise

    def _process_source_data(self, db: Session, data: list[dict[str, Any]], source: str) -> int:
        """Process and store data for a specific source."""
        if not data:
            logger.warning(f"No data received from {source}")
            return 0

        # Normalize data
        normalized_events = self.normalizer.normalize_batch(data, source)

        if not normalized_events:
            logger.warning(f"No normalized events from {source}")
            return 0

        # Store events in database
        stored_count = 0
        for event in normalized_events:
            try:
                # Check if event already exists
                existing = db.query(SignalEvent).filter(
                    SignalEvent.id == event.id
                ).first()

                if existing:
                    # Update existing event
                    existing.title = event.title
                    existing.url = event.url
                    existing.description = event.description
                    existing.timestamp = event.timestamp
                    existing.magnitude = event.magnitude
                    existing.metadata = event.metadata
                    existing.topic_id = event.topic_id
                else:
                    # Create new event
                    db.add(event)

                stored_count += 1

            except Exception as e:
                logger.error(f"Error storing event {event.id}: {e}")
                continue

        try:
            db.commit()
            logger.info(f"Stored {stored_count} events from {source}")
        except Exception as e:
            logger.error(f"Error committing {source} events: {e}")
            db.rollback()
            raise

        return stored_count

    def cleanup_old_data(self, days: int = 90) -> int:
        """Clean up old signal events."""
        logger.info(f"Cleaning up signal events older than {days} days")

        cutoff_date = datetime.utcnow() - timedelta(days=days)

        with get_db() as db:
            try:
                # Count events to be deleted
                old_events = db.query(SignalEvent).filter(
                    SignalEvent.timestamp < cutoff_date
                )

                count = old_events.count()

                # Delete old events
                old_events.delete(synchronize_session=False)
                db.commit()

                logger.info(f"Cleaned up {count} old signal events")
                return count

            except Exception as e:
                logger.error(f"Error cleaning up old data: {e}")
                db.rollback()
                raise

    def get_etl_status(self) -> dict[str, Any]:
        """Get status of ETL pipeline."""
        with get_db() as db:
            try:
                # Get total event counts by source
                source_counts = {}
                for source in ["arxiv", "github", "jobs", "funding"]:
                    count = db.query(SignalEvent).filter(
                        SignalEvent.source == source
                    ).count()
                    source_counts[source] = count

                # Get recent activity (last 24 hours)
                recent_cutoff = datetime.utcnow() - timedelta(hours=24)
                recent_count = db.query(SignalEvent).filter(
                    SignalEvent.timestamp >= recent_cutoff
                ).count()

                # Get oldest and newest events
                oldest_event = db.query(SignalEvent).order_by(
                    SignalEvent.timestamp.asc()
                ).first()

                newest_event = db.query(SignalEvent).order_by(
                    SignalEvent.timestamp.desc()
                ).first()

                return {
                    "source_counts": source_counts,
                    "total_events": sum(source_counts.values()),
                    "recent_events_24h": recent_count,
                    "oldest_event_date": oldest_event.timestamp.isoformat() if oldest_event else None,
                    "newest_event_date": newest_event.timestamp.isoformat() if newest_event else None,
                    "oracle_mode": settings.oracle_mode,
                    "last_run": datetime.utcnow().isoformat()
                }

            except Exception as e:
                logger.error(f"Error getting ETL status: {e}")
                return {"error": str(e)}


def main():
    """Main function for running ETL from command line."""
    import typer

    app = typer.Typer()

    @app.command()
    def run_full(days: int = 7):
        """Run full ETL pipeline."""
        runner = ETLRunner()
        results = runner.run_full_etl(days=days)

        print("ETL Results:")
        for source, count in results.items():
            print(f"  {source}: {count} events")
        print(f"Total: {sum(results.values())} events")

    @app.command()
    def run_source(source: str, days: int = 7):
        """Run ETL for specific source."""
        runner = ETLRunner()
        count = runner.run_source_etl(source=source, days=days)
        print(f"Processed {count} events from {source}")

    @app.command()
    def status():
        """Get ETL status."""
        runner = ETLRunner()
        status_info = runner.get_etl_status()

        print("ETL Status:")
        print(f"  Oracle Mode: {status_info.get('oracle_mode', 'unknown')}")
        print(f"  Total Events: {status_info.get('total_events', 0)}")
        print(f"  Recent Events (24h): {status_info.get('recent_events_24h', 0)}")

        print("\nEvents by Source:")
        for source, count in status_info.get('source_counts', {}).items():
            print(f"  {source}: {count}")

    @app.command()
    def cleanup(days: int = 90):
        """Clean up old data."""
        runner = ETLRunner()
        count = runner.cleanup_old_data(days=days)
        print(f"Cleaned up {count} old events")

    app()


if __name__ == "__main__":
    main()
