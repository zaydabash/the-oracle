"""GitHub API client for The Oracle."""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional

import requests

from ..core.config import settings
from ..core.logging import get_logger

logger = get_logger(__name__)


class GitHubClient:
    """Client for fetching GitHub repository data."""
    
    def __init__(self):
        self.base_url = "https://api.github.com"
        self.token = settings.github_token
        self.mock_data_path = Path("data/mock/github_mock.json")
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "TheOracle/1.0"
        }
        
        if self.token:
            self.headers["Authorization"] = f"token {self.token}"
    
    def fetch_trending_repos(self, days: int = 7, language: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetch trending repositories."""
        if settings.is_mock_mode:
            return self._load_mock_data()
        
        return self._fetch_live_trending(days, language)
    
    def _fetch_live_trending(self, days: int, language: Optional[str]) -> List[Dict[str, Any]]:
        """Fetch live trending repositories."""
        repos = []
        
        try:
            # Calculate date range
            since_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
            
            # Build search query
            query_parts = [f"created:>={since_date}"]
            if language:
                query_parts.append(f"language:{language}")
            query_parts.append("stars:>10")  # Only repos with some stars
            
            query = " ".join(query_parts)
            
            # Search for repositories
            params = {
                "q": query,
                "sort": "stars",
                "order": "desc",
                "per_page": 100
            }
            
            response = requests.get(
                f"{self.base_url}/search/repositories",
                headers=self.headers,
                params=params,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            
            for repo_data in data.get("items", []):
                repo = self._parse_github_repo(repo_data)
                if repo:
                    repos.append(repo)
            
            logger.info(f"Fetched {len(repos)} trending repositories from GitHub")
            
        except Exception as e:
            logger.error(f"Error fetching GitHub trending repos: {e}")
        
        return repos
    
    def _parse_github_repo(self, repo_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse GitHub repository data into standardized format."""
        try:
            return {
                "id": f"github:{repo_data['full_name']}",
                "name": repo_data["name"],
                "full_name": repo_data["full_name"],
                "description": repo_data.get("description", ""),
                "html_url": repo_data["html_url"],
                "language": repo_data.get("language", ""),
                "stargazers_count": repo_data["stargazers_count"],
                "forks_count": repo_data["forks_count"],
                "watchers_count": repo_data["watchers_count"],
                "created_at": repo_data["created_at"],
                "updated_at": repo_data["updated_at"],
                "pushed_at": repo_data["pushed_at"],
                "topics": repo_data.get("topics", []),
                "size": repo_data.get("size", 0),
                "open_issues_count": repo_data.get("open_issues_count", 0),
                "license": repo_data.get("license", {}).get("name") if repo_data.get("license") else None
            }
            
        except Exception as e:
            logger.error(f"Error parsing GitHub repository data: {e}")
            return None
    
    def _load_mock_data(self) -> List[Dict[str, Any]]:
        """Load mock data from JSON file."""
        try:
            if self.mock_data_path.exists():
                with open(self.mock_data_path, 'r', encoding='utf-8') as f:
                    mock_data = json.load(f)
                    logger.info(f"Loaded {len(mock_data)} mock GitHub repositories")
                    return mock_data
            else:
                logger.warning(f"Mock data file not found: {self.mock_data_path}")
                return []
        except Exception as e:
            logger.error(f"Error loading mock GitHub data: {e}")
            return []
    
    def fetch_repo_commits(self, owner: str, repo: str, days: int = 7) -> List[Dict[str, Any]]:
        """Fetch recent commits for a repository."""
        if settings.is_mock_mode:
            return []
        
        try:
            since_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            params = {
                "since": since_date,
                "per_page": 100
            }
            
            response = requests.get(
                f"{self.base_url}/repos/{owner}/{repo}/commits",
                headers=self.headers,
                params=params,
                timeout=30
            )
            response.raise_for_status()
            
            commits = response.json()
            return commits
            
        except Exception as e:
            logger.error(f"Error fetching commits for {owner}/{repo}: {e}")
            return []
    
    def search_repositories(self, query: str, language: Optional[str] = None, max_results: int = 50) -> List[Dict[str, Any]]:
        """Search repositories by query."""
        if settings.is_mock_mode:
            return self._search_mock_data(query, max_results)
        
        try:
            query_parts = [query]
            if language:
                query_parts.append(f"language:{language}")
            
            search_query = " ".join(query_parts)
            
            params = {
                "q": search_query,
                "sort": "stars",
                "order": "desc",
                "per_page": min(max_results, 100)
            }
            
            response = requests.get(
                f"{self.base_url}/search/repositories",
                headers=self.headers,
                params=params,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            repos = []
            
            for repo_data in data.get("items", []):
                repo = self._parse_github_repo(repo_data)
                if repo:
                    repos.append(repo)
            
            return repos
            
        except Exception as e:
            logger.error(f"Error searching GitHub repositories: {e}")
            return []
    
    def _search_mock_data(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """Search mock data by query."""
        mock_data = self._load_mock_data()
        if not mock_data:
            return []
        
        # Simple keyword matching in name, description, and topics
        query_lower = query.lower()
        filtered_repos = []
        
        for repo in mock_data:
            name_match = query_lower in repo.get('name', '').lower()
            desc_match = query_lower in repo.get('description', '').lower()
            topics_match = any(query_lower in topic.lower() for topic in repo.get('topics', []))
            
            if name_match or desc_match or topics_match:
                filtered_repos.append(repo)
                
                if len(filtered_repos) >= max_results:
                    break
        
        return filtered_repos
