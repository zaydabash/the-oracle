"""Topic mapping functionality for The Oracle."""

import json
import re

from ..core.config import settings
from ..core.logging import get_logger
from ..db.session import get_db
from ..models.signal_event import SignalEvent
from ..models.topic import Topic

logger = get_logger(__name__)


class TopicMapper:
    """Maps signal events to topics based on keywords and content analysis."""

    def __init__(self):
        self.topic_keywords = self._load_topic_keywords()
        self.keyword_cache = {}
        self._build_keyword_cache()

    def _load_topic_keywords(self) -> dict[str, dict[str, list[str]]]:
        """Load topic keywords from JSON file."""
        try:
            keywords_path = settings.topic_keywords_path
            if keywords_path.exists():
                with open(keywords_path, encoding='utf-8') as f:
                    data = json.load(f)
                    # Convert to dict for easier lookup
                    topics_dict = {}
                    for topic in data.get("topics", []):
                        topics_dict[topic["id"]] = {
                            "name": topic["name"],
                            "keywords": topic["keywords"]
                        }
                    return topics_dict
            else:
                logger.warning(f"Topic keywords file not found: {keywords_path}")
                return {}
        except Exception as e:
            logger.error(f"Error loading topic keywords: {e}")
            return {}

    def _build_keyword_cache(self):
        """Build keyword cache for faster matching."""
        for topic_id, topic_data in self.topic_keywords.items():
            keywords = topic_data["keywords"]
            # Create lowercase versions for case-insensitive matching
            self.keyword_cache[topic_id] = [kw.lower() for kw in keywords]

    def map_event_to_topic(self, event: SignalEvent) -> str | None:
        """Map a signal event to a topic based on content analysis."""
        # Combine title and description for analysis
        content = f"{event.title} {event.description or ''}".lower()

        # Get metadata content if available
        if event.metadata:
            if isinstance(event.metadata, dict):
                # Extract relevant metadata fields
                metadata_content = []
                for key in ['topics', 'keywords', 'categories', 'language']:
                    if key in event.metadata:
                        value = event.metadata[key]
                        if isinstance(value, list):
                            metadata_content.extend(str(item).lower() for item in value)
                        else:
                            metadata_content.append(str(value).lower())

                if metadata_content:
                    content += " " + " ".join(metadata_content)

        # Find best matching topic
        best_match = self._find_best_topic_match(content)
        return best_match

    def _find_best_topic_match(self, content: str) -> str | None:
        """Find the best matching topic for given content."""
        topic_scores = {}

        for topic_id, keywords in self.keyword_cache.items():
            score = self._calculate_keyword_score(content, keywords)
            if score > 0:
                topic_scores[topic_id] = score

        if not topic_scores:
            return None

        # Return topic with highest score
        best_topic = max(topic_scores.items(), key=lambda x: x[1])
        return best_topic[0] if best_topic[1] > 0 else None

    def _calculate_keyword_score(self, content: str, keywords: list[str]) -> float:
        """Calculate keyword matching score."""
        if not keywords:
            return 0.0

        score = 0.0
        matched_keywords = 0

        for keyword in keywords:
            # Check for exact matches
            if keyword in content:
                score += 1.0
                matched_keywords += 1
            else:
                # Check for partial matches (word boundaries)
                pattern = r'\b' + re.escape(keyword) + r'\b'
                if re.search(pattern, content):
                    score += 0.8
                    matched_keywords += 1
                else:
                    # Check for substring matches
                    if keyword in content:
                        score += 0.5

        # Normalize by total keywords
        if matched_keywords > 0:
            score = score / len(keywords)
            # Boost score if multiple keywords match
            if matched_keywords > 1:
                score *= (1 + 0.1 * matched_keywords)

        return score

    def map_events_batch(self, events: list[SignalEvent]) -> dict[str, str]:
        """Map a batch of events to topics."""
        mappings = {}

        for event in events:
            topic_id = self.map_event_to_topic(event)
            if topic_id:
                mappings[event.id] = topic_id

        logger.info(f"Mapped {len(mappings)} out of {len(events)} events to topics")
        return mappings

    def update_event_topics(self, mappings: dict[str, str]) -> int:
        """Update topic_id for events in database."""
        updated_count = 0

        with get_db() as db:
            try:
                for event_id, topic_id in mappings.items():
                    event = db.query(SignalEvent).filter(
                        SignalEvent.id == event_id
                    ).first()

                    if event:
                        event.topic_id = topic_id
                        updated_count += 1

                db.commit()
                logger.info(f"Updated topic_id for {updated_count} events")

            except Exception as e:
                logger.error(f"Error updating event topics: {e}")
                db.rollback()
                raise

        return updated_count

    def get_unmapped_events(self, limit: int = 100) -> list[SignalEvent]:
        """Get events that haven't been mapped to topics yet."""
        with get_db() as db:
            events = db.query(SignalEvent).filter(
                SignalEvent.topic_id.is_(None)
            ).limit(limit).all()

            return events

    def process_unmapped_events(self, batch_size: int = 100) -> int:
        """Process unmapped events and assign topics."""
        total_processed = 0

        while True:
            # Get batch of unmapped events
            unmapped_events = self.get_unmapped_events(limit=batch_size)

            if not unmapped_events:
                break

            # Map events to topics
            mappings = self.map_events_batch(unmapped_events)

            if mappings:
                # Update database
                updated = self.update_event_topics(mappings)
                total_processed += updated

            # If we got fewer events than batch size, we're done
            if len(unmapped_events) < batch_size:
                break

        logger.info(f"Processed {total_processed} unmapped events")
        return total_processed

    def get_topic_statistics(self) -> dict[str, int]:
        """Get statistics about topic mappings."""
        with get_db() as db:
            # Count events by topic
            topic_counts = {}
            topics = db.query(Topic).all()

            for topic in topics:
                count = db.query(SignalEvent).filter(
                    SignalEvent.topic_id == topic.id
                ).count()
                topic_counts[topic.name] = count

            # Count unmapped events
            unmapped_count = db.query(SignalEvent).filter(
                SignalEvent.topic_id.is_(None)
            ).count()

            topic_counts["Unmapped"] = unmapped_count

            return topic_counts

    def add_topic_keywords(self, topic_id: str, keywords: list[str]) -> bool:
        """Add keywords to a topic."""
        try:
            if topic_id in self.topic_keywords:
                existing_keywords = self.topic_keywords[topic_id]["keywords"]
                new_keywords = list(set(existing_keywords + keywords))
                self.topic_keywords[topic_id]["keywords"] = new_keywords

                # Update cache
                self.keyword_cache[topic_id] = [kw.lower() for kw in new_keywords]

                logger.info(f"Added {len(keywords)} keywords to topic {topic_id}")
                return True
            else:
                logger.warning(f"Topic {topic_id} not found")
                return False
        except Exception as e:
            logger.error(f"Error adding keywords to topic {topic_id}: {e}")
            return False

    def create_topic_from_events(self, topic_id: str, topic_name: str,
                                event_ids: list[str]) -> bool:
        """Create a new topic based on keywords extracted from events."""
        try:
            with get_db() as db:
                # Get events
                events = db.query(SignalEvent).filter(
                    SignalEvent.id.in_(event_ids)
                ).all()

                if not events:
                    logger.warning(f"No events found for topic creation: {topic_id}")
                    return False

                # Extract keywords from events
                keywords = self._extract_keywords_from_events(events)

                # Create topic
                topic = Topic(
                    id=topic_id,
                    name=topic_name,
                    keywords=keywords
                )

                db.add(topic)

                # Update events with topic_id
                for event in events:
                    event.topic_id = topic_id

                db.commit()

                # Update local cache
                self.topic_keywords[topic_id] = {
                    "name": topic_name,
                    "keywords": keywords
                }
                self.keyword_cache[topic_id] = [kw.lower() for kw in keywords]

                logger.info(f"Created topic {topic_id} with {len(keywords)} keywords")
                return True

        except Exception as e:
            logger.error(f"Error creating topic {topic_id}: {e}")
            return False

    def _extract_keywords_from_events(self, events: list[SignalEvent]) -> list[str]:
        """Extract keywords from a list of events."""
        # Combine all content
        all_content = []
        for event in events:
            content = f"{event.title} {event.description or ''}"
            all_content.append(content)

        # Simple keyword extraction (can be enhanced with NLP)
        combined_content = " ".join(all_content).lower()

        # Extract common words (simple approach)
        words = re.findall(r'\b[a-z]{3,}\b', combined_content)

        # Count word frequency
        word_counts = {}
        for word in words:
            word_counts[word] = word_counts.get(word, 0) + 1

        # Return most common words as keywords
        sorted_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)
        keywords = [word for word, count in sorted_words[:20] if count > 1]

        return keywords
