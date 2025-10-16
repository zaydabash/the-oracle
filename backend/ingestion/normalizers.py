"""Data normalizers for converting raw data to standardized SignalEvent format."""

from datetime import datetime
from typing import Any

from ..core.logging import get_logger
from ..models.signal_event import SignalEvent

logger = get_logger(__name__)


class SignalEventNormalizer:
    """Normalizer for converting raw data to SignalEvent format."""

    def __init__(self):
        self.source_weights = {
            "arxiv": 1.0,
            "github": 2.0,  # Higher weight for code activity
            "jobs": 1.5,    # Job postings indicate market demand
            "funding": 3.0   # Funding indicates strong interest
        }

    def normalize_arxiv_paper(self, paper: dict[str, Any]) -> SignalEvent | None:
        """Normalize arXiv paper to SignalEvent."""
        try:
            # Calculate magnitude based on paper recency and category
            magnitude = self._calculate_paper_magnitude(paper)

            # Parse timestamps
            published = self._parse_timestamp(paper.get("published"))
            updated = self._parse_timestamp(paper.get("updated"))

            # Use updated time if available, otherwise published time
            timestamp = updated or published or datetime.utcnow()

            # Create metadata
            metadata = {
                "authors": paper.get("authors", []),
                "categories": paper.get("categories", []),
                "primary_category": paper.get("primary_category"),
                "pdf_url": paper.get("pdf_url"),
                "abstract": paper.get("abstract", "")[:500]  # Truncate for storage
            }

            return SignalEvent(
                id=paper["id"],
                source="arxiv",
                source_id=paper["id"].replace("arxiv:", ""),
                title=paper["title"],
                url=paper.get("url"),
                description=paper.get("abstract", "")[:1000],  # Truncate for storage
                timestamp=timestamp,
                magnitude=magnitude,
                metadata=metadata
            )

        except Exception as e:
            logger.error(f"Error normalizing arXiv paper: {e}")
            return None

    def normalize_github_repo(self, repo: dict[str, Any]) -> SignalEvent | None:
        """Normalize GitHub repository to SignalEvent."""
        try:
            # Calculate magnitude based on stars, forks, and activity
            magnitude = self._calculate_repo_magnitude(repo)

            # Parse timestamps
            created = self._parse_timestamp(repo.get("created_at"))
            updated = self._parse_timestamp(repo.get("updated_at"))
            pushed = self._parse_timestamp(repo.get("pushed_at"))

            # Use pushed time if available (indicates recent activity), otherwise updated
            timestamp = pushed or updated or created or datetime.utcnow()

            # Create metadata
            metadata = {
                "language": repo.get("language"),
                "stargazers_count": repo.get("stargazers_count", 0),
                "forks_count": repo.get("forks_count", 0),
                "watchers_count": repo.get("watchers_count", 0),
                "topics": repo.get("topics", []),
                "size": repo.get("size", 0),
                "open_issues_count": repo.get("open_issues_count", 0),
                "license": repo.get("license"),
                "created_at": repo.get("created_at"),
                "updated_at": repo.get("updated_at")
            }

            return SignalEvent(
                id=repo["id"],
                source="github",
                source_id=repo["full_name"],
                title=repo["name"],
                url=repo["html_url"],
                description=repo.get("description", ""),
                timestamp=timestamp,
                magnitude=magnitude,
                metadata=metadata
            )

        except Exception as e:
            logger.error(f"Error normalizing GitHub repository: {e}")
            return None

    def normalize_job_posting(self, job: dict[str, Any]) -> SignalEvent | None:
        """Normalize job posting to SignalEvent."""
        try:
            # Calculate magnitude based on salary and company size indicators
            magnitude = self._calculate_job_magnitude(job)

            # Parse timestamp
            published = self._parse_timestamp(job.get("published"))
            timestamp = published or datetime.utcnow()

            # Create metadata
            metadata = {
                "company": job.get("company"),
                "location": job.get("location"),
                "salary": job.get("salary"),
                "keywords": job.get("keywords", []),
                "source": job.get("source")
            }

            return SignalEvent(
                id=job["id"],
                source="jobs",
                source_id=job["id"].replace("job:", ""),
                title=job["title"],
                url=job.get("url"),
                description=job.get("description", "")[:1000],  # Truncate for storage
                timestamp=timestamp,
                magnitude=magnitude,
                metadata=metadata
            )

        except Exception as e:
            logger.error(f"Error normalizing job posting: {e}")
            return None

    def normalize_funding_round(self, funding: dict[str, Any]) -> SignalEvent | None:
        """Normalize funding round to SignalEvent."""
        try:
            # Calculate magnitude based on funding amount
            magnitude = self._calculate_funding_magnitude(funding)

            # Parse timestamp
            announced = self._parse_timestamp(funding.get("announced_date"))
            timestamp = announced or datetime.utcnow()

            # Create metadata
            metadata = {
                "company": funding.get("company"),
                "funding_type": funding.get("funding_type"),
                "amount": funding.get("amount"),
                "currency": funding.get("currency"),
                "investors": funding.get("investors", [])
            }

            return SignalEvent(
                id=funding["id"],
                source="funding",
                source_id=funding["id"].replace("funding:", ""),
                title=f"{funding.get('company', 'Company')} - {funding.get('funding_type', 'Funding')}",
                url=funding.get("url"),
                description=funding.get("description", ""),
                timestamp=timestamp,
                magnitude=magnitude,
                metadata=metadata
            )

        except Exception as e:
            logger.error(f"Error normalizing funding round: {e}")
            return None

    def _calculate_paper_magnitude(self, paper: dict[str, Any]) -> float:
        """Calculate magnitude for arXiv paper."""
        base_weight = self.source_weights["arxiv"]

        # Boost for AI/ML categories
        categories = paper.get("categories", [])
        ai_boost = 1.5 if any(cat.startswith("cs.AI") or cat.startswith("cs.LG") or cat.startswith("stat.ML") for cat in categories) else 1.0

        return base_weight * ai_boost

    def _calculate_repo_magnitude(self, repo: dict[str, Any]) -> float:
        """Calculate magnitude for GitHub repository."""
        base_weight = self.source_weights["github"]

        # Scale by stars (logarithmic)
        stars = repo.get("stargazers_count", 0)
        star_factor = 1.0 + (stars / 1000.0)  # Boost for popular repos

        # Scale by recent activity (forks indicate active development)
        forks = repo.get("forks_count", 0)
        fork_factor = 1.0 + (forks / 100.0)

        return base_weight * star_factor * fork_factor

    def _calculate_job_magnitude(self, job: dict[str, Any]) -> float:
        """Calculate magnitude for job posting."""
        base_weight = self.source_weights["jobs"]

        # Boost for high-salary positions
        salary = job.get("salary", "")
        salary_boost = 1.5 if "$" in salary and any(x in salary for x in ["k", "K", "000"]) else 1.0

        # Boost for remote positions (indicates broader market demand)
        location = job.get("location", "").lower()
        remote_boost = 1.2 if "remote" in location else 1.0

        return base_weight * salary_boost * remote_boost

    def _calculate_funding_magnitude(self, funding: dict[str, Any]) -> float:
        """Calculate magnitude for funding round."""
        base_weight = self.source_weights["funding"]

        # Scale by funding amount
        amount = funding.get("amount", 0)
        if amount:
            # Logarithmic scaling of funding amount
            import math
            amount_factor = 1.0 + math.log10(max(amount, 1000)) / 10.0
        else:
            amount_factor = 1.0

        # Boost for certain funding types
        funding_type = funding.get("funding_type", "").lower()
        type_boost = 2.0 if "series" in funding_type else 1.5 if "seed" in funding_type else 1.0

        return base_weight * amount_factor * type_boost

    def _parse_timestamp(self, timestamp_str: str | None) -> datetime | None:
        """Parse timestamp string to datetime object."""
        if not timestamp_str:
            return None

        try:
            # Handle various timestamp formats
            formats = [
                "%Y-%m-%dT%H:%M:%SZ",
                "%Y-%m-%dT%H:%M:%S.%fZ",
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d"
            ]

            for fmt in formats:
                try:
                    return datetime.strptime(timestamp_str, fmt)
                except ValueError:
                    continue

            # Try parsing with dateutil
            from dateutil import parser
            return parser.parse(timestamp_str)

        except Exception as e:
            logger.warning(f"Could not parse timestamp '{timestamp_str}': {e}")
            return None

    def normalize_batch(self, data: list[dict[str, Any]], source: str) -> list[SignalEvent]:
        """Normalize a batch of data from a specific source."""
        normalizers = {
            "arxiv": self.normalize_arxiv_paper,
            "github": self.normalize_github_repo,
            "jobs": self.normalize_job_posting,
            "funding": self.normalize_funding_round
        }

        normalizer = normalizers.get(source)
        if not normalizer:
            logger.error(f"No normalizer found for source: {source}")
            return []

        normalized_events = []
        for item in data:
            event = normalizer(item)
            if event:
                normalized_events.append(event)

        logger.info(f"Normalized {len(normalized_events)} events from {source}")
        return normalized_events
