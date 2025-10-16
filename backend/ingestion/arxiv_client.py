"""arXiv API client for The Oracle."""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional

import feedparser
import requests
from bs4 import BeautifulSoup

from ..core.config import settings
from ..core.logging import get_logger

logger = get_logger(__name__)


class ArxivClient:
    """Client for fetching arXiv papers."""
    
    def __init__(self):
        self.base_url = "http://export.arxiv.org/api/query"
        self.categories = settings.arxiv_categories
        self.mock_data_path = Path("data/mock/arxiv_mock.json")
    
    def fetch_recent_papers(self, days: int = 7, max_results: int = 100) -> List[Dict[str, Any]]:
        """Fetch recent papers from arXiv."""
        if settings.is_mock_mode:
            return self._load_mock_data()
        
        return self._fetch_live_data(days, max_results)
    
    def _fetch_live_data(self, days: int, max_results: int) -> List[Dict[str, Any]]:
        """Fetch live data from arXiv API."""
        papers = []
        
        for category in self.categories:
            try:
                # Calculate date range
                start_date = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d%H%M%S")
                
                # Build query
                query = f"cat:{category} AND submittedDate:[{start_date} TO {datetime.now().strftime('%Y%m%d%H%M%S')}]"
                
                # Make API request
                params = {
                    "search_query": query,
                    "start": 0,
                    "max_results": min(max_results, 100),
                    "sortBy": "submittedDate",
                    "sortOrder": "descending"
                }
                
                response = requests.get(self.base_url, params=params, timeout=30)
                response.raise_for_status()
                
                # Parse XML response
                feed = feedparser.parse(response.content)
                
                for entry in feed.entries:
                    paper = self._parse_arxiv_entry(entry)
                    if paper:
                        papers.append(paper)
                        
            except Exception as e:
                logger.error(f"Error fetching arXiv data for category {category}: {e}")
                continue
        
        logger.info(f"Fetched {len(papers)} papers from arXiv")
        return papers
    
    def _parse_arxiv_entry(self, entry: feedparser.FeedParserDict) -> Optional[Dict[str, Any]]:
        """Parse an arXiv entry into standardized format."""
        try:
            # Extract ID from link
            arxiv_id = entry.id.split('/')[-1] if '/' in entry.id else entry.id
            
            # Parse categories
            categories = []
            if hasattr(entry, 'tags'):
                categories = [tag.term for tag in entry.tags if hasattr(tag, 'term')]
            
            # Extract primary category
            primary_category = categories[0] if categories else "unknown"
            
            # Parse abstract
            abstract = entry.summary if hasattr(entry, 'summary') else ""
            
            # Parse authors
            authors = []
            if hasattr(entry, 'authors'):
                authors = [author.name for author in entry.authors]
            
            # Parse publication dates
            published = entry.published if hasattr(entry, 'published') else None
            updated = entry.updated if hasattr(entry, 'updated') else None
            
            return {
                "id": f"arxiv:{arxiv_id}",
                "title": entry.title,
                "authors": authors,
                "abstract": abstract,
                "categories": categories,
                "published": published,
                "updated": updated,
                "primary_category": primary_category,
                "url": entry.link,
                "pdf_url": entry.link.replace('/abs/', '/pdf/') + '.pdf'
            }
            
        except Exception as e:
            logger.error(f"Error parsing arXiv entry: {e}")
            return None
    
    def _load_mock_data(self) -> List[Dict[str, Any]]:
        """Load mock data from JSON file."""
        try:
            if self.mock_data_path.exists():
                with open(self.mock_data_path, 'r', encoding='utf-8') as f:
                    mock_data = json.load(f)
                    logger.info(f"Loaded {len(mock_data)} mock arXiv papers")
                    return mock_data
            else:
                logger.warning(f"Mock data file not found: {self.mock_data_path}")
                return []
        except Exception as e:
            logger.error(f"Error loading mock arXiv data: {e}")
            return []
    
    def search_papers(self, query: str, max_results: int = 50) -> List[Dict[str, Any]]:
        """Search papers by query."""
        if settings.is_mock_mode:
            return self._search_mock_data(query, max_results)
        
        try:
            params = {
                "search_query": query,
                "start": 0,
                "max_results": min(max_results, 100),
                "sortBy": "relevance",
                "sortOrder": "descending"
            }
            
            response = requests.get(self.base_url, params=params, timeout=30)
            response.raise_for_status()
            
            feed = feedparser.parse(response.content)
            papers = []
            
            for entry in feed.entries:
                paper = self._parse_arxiv_entry(entry)
                if paper:
                    papers.append(paper)
            
            return papers
            
        except Exception as e:
            logger.error(f"Error searching arXiv papers: {e}")
            return []
    
    def _search_mock_data(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """Search mock data by query."""
        mock_data = self._load_mock_data()
        if not mock_data:
            return []
        
        # Simple keyword matching in title and abstract
        query_lower = query.lower()
        filtered_papers = []
        
        for paper in mock_data:
            title_match = query_lower in paper.get('title', '').lower()
            abstract_match = query_lower in paper.get('abstract', '').lower()
            
            if title_match or abstract_match:
                filtered_papers.append(paper)
                
                if len(filtered_papers) >= max_results:
                    break
        
        return filtered_papers
