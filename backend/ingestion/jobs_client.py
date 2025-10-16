"""Jobs RSS client for The Oracle."""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import feedparser
import requests

from ..core.config import settings
from ..core.logging import get_logger

logger = get_logger(__name__)


class JobsClient:
    """Client for fetching job postings from RSS feeds."""

    def __init__(self):
        self.feed_urls = settings.jobs_feed_urls
        self.mock_data_path = Path("data/mock/jobs_mock.json")

    def fetch_recent_jobs(self, days: int = 7) -> list[dict[str, Any]]:
        """Fetch recent job postings."""
        if settings.is_mock_mode:
            return self._load_mock_data()

        return self._fetch_live_data(days)

    def _fetch_live_data(self, days: int) -> list[dict[str, Any]]:
        """Fetch live data from RSS feeds."""
        all_jobs = []

        for feed_url in self.feed_urls:
            try:
                jobs = self._fetch_feed(feed_url, days)
                all_jobs.extend(jobs)
                logger.info(f"Fetched {len(jobs)} jobs from {feed_url}")

            except Exception as e:
                logger.error(f"Error fetching jobs from {feed_url}: {e}")
                continue

        logger.info(f"Total fetched {len(all_jobs)} job postings")
        return all_jobs

    def _fetch_feed(self, feed_url: str, days: int) -> list[dict[str, Any]]:
        """Fetch jobs from a single RSS feed."""
        try:
            response = requests.get(feed_url, timeout=30)
            response.raise_for_status()

            feed = feedparser.parse(response.content)
            jobs = []

            cutoff_date = datetime.now() - timedelta(days=days)

            for entry in feed.entries:
                job = self._parse_job_entry(entry, feed_url)
                if job:
                    # Check if job is within date range
                    job_date = job.get('published_date')
                    if job_date and job_date >= cutoff_date:
                        jobs.append(job)

            return jobs

        except Exception as e:
            logger.error(f"Error parsing feed {feed_url}: {e}")
            return []

    def _parse_job_entry(self, entry: feedparser.FeedParserDict, source_url: str) -> dict[str, Any] | None:
        """Parse a job entry from RSS feed."""
        try:
            # Extract job details from title and description
            title = entry.title if hasattr(entry, 'title') else ""
            description = entry.description if hasattr(entry, 'description') else ""
            link = entry.link if hasattr(entry, 'link') else ""

            # Parse published date
            published_date = None
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                published_date = datetime(*entry.published_parsed[:6])
            elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                published_date = datetime(*entry.updated_parsed[:6])

            # Extract company and location from title/description
            company = self._extract_company(title, description)
            location = self._extract_location(title, description)

            # Extract salary if available
            salary = self._extract_salary(description)

            # Generate keywords from title and description
            keywords = self._extract_keywords(title, description)

            # Generate unique ID
            job_id = f"job:{urlparse(link).path.split('/')[-1]}" if link else f"job:{hash(title)}"

            return {
                "id": job_id,
                "title": title,
                "company": company,
                "location": location,
                "description": description,
                "url": link,
                "published": published_date.isoformat() if published_date else None,
                "published_date": published_date,
                "salary": salary,
                "keywords": keywords,
                "source": source_url
            }

        except Exception as e:
            logger.error(f"Error parsing job entry: {e}")
            return None

    def _extract_company(self, title: str, description: str) -> str:
        """Extract company name from title or description."""
        # Simple heuristics for company extraction
        text = f"{title} {description}".lower()

        # Look for common patterns
        if " at " in title.lower():
            parts = title.lower().split(" at ")
            if len(parts) > 1:
                return parts[1].strip().title()

        # Look for company names in description
        lines = description.split('\n')
        for line in lines[:3]:  # Check first few lines
            if any(word in line.lower() for word in ['company', 'corporation', 'inc', 'llc', 'ltd']):
                return line.strip().title()

        return "Unknown Company"

    def _extract_location(self, title: str, description: str) -> str:
        """Extract location from title or description."""
        text = f"{title} {description}".lower()

        # Look for location patterns
        location_patterns = [
            'remote', 'on-site', 'hybrid', 'new york', 'san francisco', 'london',
            'seattle', 'austin', 'boston', 'palo alto', 'mountain view'
        ]

        for pattern in location_patterns:
            if pattern in text:
                return pattern.title()

        return "Location Not Specified"

    def _extract_salary(self, description: str) -> str | None:
        """Extract salary information from description."""
        import re

        # Look for salary patterns
        salary_patterns = [
            r'\$[\d,]+(?:k|K)?(?:-\$[\d,]+(?:k|K)?)?',
            r'\$[\d,]+(?:-\$[\d,]+)?\s*(?:per\s+year|annually|year)',
            r'\$[\d,]+(?:-\$[\d,]+)?\s*(?:per\s+hour|hourly)',
        ]

        for pattern in salary_patterns:
            matches = re.findall(pattern, description, re.IGNORECASE)
            if matches:
                return matches[0]

        return None

    def _extract_keywords(self, title: str, description: str) -> list[str]:
        """Extract relevant keywords from title and description."""
        text = f"{title} {description}".lower()

        # Technology keywords
        tech_keywords = [
            'python', 'javascript', 'typescript', 'react', 'angular', 'vue',
            'node.js', 'django', 'flask', 'fastapi', 'machine learning', 'ai',
            'artificial intelligence', 'data science', 'deep learning',
            'computer vision', 'nlp', 'natural language processing',
            'blockchain', 'cryptocurrency', 'web3', 'defi',
            'cloud', 'aws', 'azure', 'gcp', 'docker', 'kubernetes',
            'microservices', 'api', 'rest', 'graphql',
            'frontend', 'backend', 'full stack', 'fullstack',
            'mobile', 'ios', 'android', 'react native',
            'database', 'sql', 'nosql', 'postgresql', 'mongodb',
            'devops', 'ci/cd', 'jenkins', 'gitlab',
            'agile', 'scrum', 'kanban'
        ]

        found_keywords = []
        for keyword in tech_keywords:
            if keyword in text:
                found_keywords.append(keyword)

        return found_keywords

    def _load_mock_data(self) -> list[dict[str, Any]]:
        """Load mock data from JSON file."""
        try:
            if self.mock_data_path.exists():
                with open(self.mock_data_path, encoding='utf-8') as f:
                    mock_data = json.load(f)
                    logger.info(f"Loaded {len(mock_data)} mock job postings")
                    return mock_data
            else:
                logger.warning(f"Mock data file not found: {self.mock_data_path}")
                return []
        except Exception as e:
            logger.error(f"Error loading mock jobs data: {e}")
            return []
