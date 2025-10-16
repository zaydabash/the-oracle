#!/usr/bin/env python3
"""Development seed script for The Oracle."""

import json
import logging
import sys
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import List, Dict, Any
import uuid

# Add backend to path
sys.path.append(str(Path(__file__).parent.parent / "backend"))

from backend.core.config import settings
from backend.core.logging import setup_logging, get_logger
from backend.db.base import engine
from backend.db.base import Base
from backend.db.session import SessionLocal
from backend.models.topic import Topic
from backend.models.signal_event import SignalEvent
from backend.models.features import TopicFeatures
from backend.models.forecast import TopicForecast
from backend.ingestion.etl_runner import ETLRunner
from backend.features.build_feature_matrix import FeatureMatrixBuilder
from backend.forecasting.baseline import BaselineForecaster
from backend.features.topic_mapping import TopicMapper

logger = get_logger(__name__)


def load_topics_from_json() -> List[Dict[str, Any]]:
    """Load topics from topic_keywords.json."""
    try:
        keywords_path = settings.topic_keywords_path
        if keywords_path.exists():
            with open(keywords_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get("topics", [])
        else:
            logger.warning(f"Topic keywords file not found: {keywords_path}")
            return []
    except Exception as e:
        logger.error(f"Error loading topics: {e}")
        return []


def seed_topics(db_session, topics_data: List[Dict[str, Any]]) -> int:
    """Seed topics in database."""
    logger.info("Seeding topics...")
    
    created_count = 0
    
    for topic_data in topics_data:
        try:
            # Check if topic already exists
            existing = db_session.query(Topic).filter(Topic.id == topic_data["id"]).first()
            
            if existing:
                logger.info(f"Topic {topic_data['id']} already exists, skipping")
                continue
            
            # Create topic
            topic = Topic(
                id=topic_data["id"],
                name=topic_data["name"],
                keywords=topic_data["keywords"],
                description=f"Technology domain: {topic_data['name']}"
            )
            
            db_session.add(topic)
            created_count += 1
            
        except Exception as e:
            logger.error(f"Error creating topic {topic_data['id']}: {e}")
    
    try:
        db_session.commit()
        logger.info(f"Created {created_count} topics")
    except Exception as e:
        logger.error(f"Error committing topics: {e}")
        db_session.rollback()
        raise
    
    return created_count


def load_mock_events() -> Dict[str, List[Dict[str, Any]]]:
    """Load mock events from JSON files."""
    mock_data = {}
    
    mock_files = {
        "arxiv": "data/mock/arxiv_mock.json",
        "github": "data/mock/github_mock.json", 
        "jobs": "data/mock/jobs_mock.json",
        "funding": "data/mock/funding_mock.json"
    }
    
    for source, file_path in mock_files.items():
        try:
            path = Path(file_path)
            if path.exists():
                with open(path, 'r', encoding='utf-8') as f:
                    mock_data[source] = json.load(f)
                    logger.info(f"Loaded {len(mock_data[source])} mock events from {source}")
            else:
                logger.warning(f"Mock file not found: {path}")
                mock_data[source] = []
        except Exception as e:
            logger.error(f"Error loading mock data from {source}: {e}")
            mock_data[source] = []
    
    return mock_data


def seed_mock_events(db_session, mock_data: Dict[str, List[Dict[str, Any]]]) -> int:
    """Seed mock events in database."""
    logger.info("Seeding mock events...")
    
    from backend.ingestion.normalizers import SignalEventNormalizer
    normalizer = SignalEventNormalizer()
    
    total_created = 0
    
    for source, events in mock_data.items():
        logger.info(f"Processing {len(events)} {source} events...")
        
        # Normalize events
        if source == "arxiv":
            normalized_events = [normalizer.normalize_arxiv_paper(event) for event in events]
        elif source == "github":
            normalized_events = [normalizer.normalize_github_repo(event) for event in events]
        elif source == "jobs":
            normalized_events = [normalizer.normalize_job_posting(event) for event in events]
        elif source == "funding":
            normalized_events = [normalizer.normalize_funding_round(event) for event in events]
        else:
            continue
        
        # Filter out None values
        normalized_events = [event for event in normalized_events if event is not None]
        
        # Store events
        for event in normalized_events:
            try:
                # Check if event already exists
                existing = db_session.query(SignalEvent).filter(SignalEvent.id == event.id).first()
                
                if existing:
                    continue
                
                db_session.add(event)
                total_created += 1
                
            except Exception as e:
                logger.error(f"Error storing event {event.id}: {e}")
                continue
        
        logger.info(f"Created {len(normalized_events)} {source} events")
    
    try:
        db_session.commit()
        logger.info(f"Total created {total_created} events")
    except Exception as e:
        logger.error(f"Error committing events: {e}")
        db_session.rollback()
        raise
    
    return total_created


def map_events_to_topics(db_session) -> int:
    """Map events to topics using topic mapper."""
    logger.info("Mapping events to topics...")
    
    mapper = TopicMapper()
    mapped_count = mapper.process_unmapped_events(batch_size=100)
    
    logger.info(f"Mapped {mapped_count} events to topics")
    return mapped_count


def generate_features(db_session) -> int:
    """Generate features for topics."""
    logger.info("Generating features...")
    
    builder = FeatureMatrixBuilder()
    results = builder.build_feature_matrix(days=90, force_rebuild=True)
    
    total_features = sum(results.values())
    logger.info(f"Generated {total_features} feature records")
    
    return total_features


def generate_forecasts(db_session) -> int:
    """Generate forecasts for topics."""
    logger.info("Generating forecasts...")
    
    forecaster = BaselineForecaster()
    results = forecaster.forecast_all_topics(force_rebuild=True)
    
    total_forecasts = sum(
        sum(topic_results.values()) if isinstance(topic_results, dict) else 0
        for topic_results in results.values()
        if isinstance(topic_results, dict) and "error" not in topic_results
    )
    
    logger.info(f"Generated {total_forecasts} forecasts")
    
    return total_forecasts


def main():
    """Main seeding function."""
    setup_logging()
    logger.info("Starting development seed process")
    
    try:
        # Create database tables
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created/verified")
        
        # Create database session
        db_session = SessionLocal()
        
        try:
            # Step 1: Load and seed topics
            topics_data = load_topics_from_json()
            if topics_data:
                topics_created = seed_topics(db_session, topics_data)
                logger.info(f"✓ Seeded {topics_created} topics")
            else:
                logger.warning("No topics to seed")
                return
            
            # Step 2: Load and seed mock events
            mock_data = load_mock_events()
            if any(mock_data.values()):
                events_created = seed_mock_events(db_session, mock_data)
                logger.info(f"✓ Seeded {events_created} events")
            else:
                logger.warning("No mock events to seed")
                return
            
            # Step 3: Map events to topics
            mapped_count = map_events_to_topics(db_session)
            logger.info(f"✓ Mapped {mapped_count} events to topics")
            
            # Step 4: Generate features
            features_count = generate_features(db_session)
            logger.info(f"✓ Generated {features_count} features")
            
            # Step 5: Generate forecasts
            forecasts_count = generate_forecasts(db_session)
            logger.info(f"✓ Generated {forecasts_count} forecasts")
            
            logger.info("Development seed completed successfully!")
            
            # Print summary
            print("\n" + "="*50)
            print("THE ORACLE - DEVELOPMENT SEED SUMMARY")
            print("="*50)
            print(f"Topics created: {len(topics_data)}")
            print(f"Events created: {sum(len(events) for events in mock_data.values())}")
            print(f"Events mapped to topics: {mapped_count}")
            print(f"Features generated: {features_count}")
            print(f"Forecasts generated: {forecasts_count}")
            print("\nThe Oracle is ready!")
            print("Visit http://localhost:5173 for the dashboard")
            print("Visit http://localhost:8000/docs for API documentation")
            print("="*50)
            
        finally:
            db_session.close()
            
    except Exception as e:
        logger.error(f"Seed process failed: {e}")
        raise


if __name__ == "__main__":
    main()
