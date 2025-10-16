"""Crunchbase API client for The Oracle."""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import requests

from ..core.config import settings
from ..core.logging import get_logger

logger = get_logger(__name__)


class CrunchbaseClient:
    """Client for fetching funding data from Crunchbase."""

    def __init__(self):
        self.api_key = settings.crunchbase_api_key
        self.base_url = "https://api.crunchbase.com/v4"
        self.mock_data_path = Path("data/mock/funding_mock.json")
        self.headers = {
            "X-cb-user-key": self.api_key,
            "Accept": "application/json"
        } if self.api_key else {}

    def fetch_recent_funding(self, days: int = 30) -> list[dict[str, Any]]:
        """Fetch recent funding rounds."""
        if settings.is_mock_mode or not self.api_key:
            return self._load_mock_data()

        return self._fetch_live_data(days)

    def _fetch_live_data(self, days: int) -> list[dict[str, Any]]:
        """Fetch live data from Crunchbase API."""
        funding_rounds = []

        try:
            # Calculate date range
            since_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

            # Build query parameters
            params = {
                "field_ids": [
                    "identifier", "name", "short_description", "funding_type",
                    "money_raised", "announced_on", "investor_identifiers",
                    "organization_identifier"
                ],
                "query": {
                    "predicates": [
                        {
                            "field_id": "announced_on",
                            "operator_id": "gte",
                            "values": [since_date]
                        }
                    ]
                },
                "limit": 100,
                "order": [
                    {
                        "field_id": "announced_on",
                        "direction": "desc"
                    }
                ]
            }

            response = requests.post(
                f"{self.base_url}/searches/funding_rounds",
                headers=self.headers,
                json=params,
                timeout=30
            )
            response.raise_for_status()

            data = response.json()

            for item in data.get("entities", []):
                funding_round = self._parse_funding_round(item)
                if funding_round:
                    funding_rounds.append(funding_round)

            logger.info(f"Fetched {len(funding_rounds)} funding rounds from Crunchbase")

        except Exception as e:
            logger.error(f"Error fetching Crunchbase funding data: {e}")

        return funding_rounds

    def _parse_funding_round(self, item: dict[str, Any]) -> dict[str, Any] | None:
        """Parse Crunchbase funding round data."""
        try:
            properties = item.get("properties", {})
            identifier = properties.get("identifier", {})

            # Extract funding amount
            money_raised = properties.get("money_raised")
            amount = None
            currency = "USD"

            if money_raised:
                amount = money_raised.get("value")
                currency = money_raised.get("currency_code", "USD")

            # Extract investors
            investors = []
            investor_identifiers = properties.get("investor_identifiers", [])
            for inv in investor_identifiers:
                if isinstance(inv, dict) and "name" in inv:
                    investors.append(inv["name"])

            # Extract organization info
            org_identifier = properties.get("organization_identifier", {})
            company_name = org_identifier.get("name", "Unknown Company")

            return {
                "id": f"funding:{identifier.get('uuid', '')}",
                "company": company_name,
                "description": properties.get("short_description", ""),
                "funding_type": properties.get("funding_type", ""),
                "amount": amount,
                "currency": currency,
                "announced_date": properties.get("announced_on"),
                "investors": investors,
                "url": f"https://www.crunchbase.com/funding_round/{identifier.get('uuid', '')}"
            }

        except Exception as e:
            logger.error(f"Error parsing Crunchbase funding round: {e}")
            return None

    def _load_mock_data(self) -> list[dict[str, Any]]:
        """Load mock data from JSON file."""
        try:
            if self.mock_data_path.exists():
                with open(self.mock_data_path, encoding='utf-8') as f:
                    mock_data = json.load(f)
                    logger.info(f"Loaded {len(mock_data)} mock funding rounds")
                    return mock_data
            else:
                logger.warning(f"Mock data file not found: {self.mock_data_path}")
                return []
        except Exception as e:
            logger.error(f"Error loading mock funding data: {e}")
            return []

    def search_funding(self, query: str, max_results: int = 50) -> list[dict[str, Any]]:
        """Search funding rounds by query."""
        if settings.is_mock_mode or not self.api_key:
            return self._search_mock_data(query, max_results)

        try:
            params = {
                "field_ids": [
                    "identifier", "name", "short_description", "funding_type",
                    "money_raised", "announced_on", "investor_identifiers",
                    "organization_identifier"
                ],
                "query": {
                    "predicates": [
                        {
                            "field_id": "name",
                            "operator_id": "contains",
                            "values": [query]
                        }
                    ]
                },
                "limit": min(max_results, 100),
                "order": [
                    {
                        "field_id": "announced_on",
                        "direction": "desc"
                    }
                ]
            }

            response = requests.post(
                f"{self.base_url}/searches/funding_rounds",
                headers=self.headers,
                json=params,
                timeout=30
            )
            response.raise_for_status()

            data = response.json()
            funding_rounds = []

            for item in data.get("entities", []):
                funding_round = self._parse_funding_round(item)
                if funding_round:
                    funding_rounds.append(funding_round)

            return funding_rounds

        except Exception as e:
            logger.error(f"Error searching Crunchbase funding: {e}")
            return []

    def _search_mock_data(self, query: str, max_results: int) -> list[dict[str, Any]]:
        """Search mock data by query."""
        mock_data = self._load_mock_data()
        if not mock_data:
            return []

        # Simple keyword matching in company name and description
        query_lower = query.lower()
        filtered_funding = []

        for funding in mock_data:
            company_match = query_lower in funding.get('company', '').lower()
            desc_match = query_lower in funding.get('description', '').lower()

            if company_match or desc_match:
                filtered_funding.append(funding)

                if len(filtered_funding) >= max_results:
                    break

        return filtered_funding

    def get_funding_trends(self, days: int = 90) -> dict[str, Any]:
        """Get funding trend analysis."""
        funding_rounds = self.fetch_recent_funding(days)

        if not funding_rounds:
            return {"total_amount": 0, "round_count": 0, "average_amount": 0}

        total_amount = sum(
            f.get("amount", 0) for f in funding_rounds
            if f.get("amount") is not None
        )

        round_count = len(funding_rounds)
        average_amount = total_amount / round_count if round_count > 0 else 0

        # Group by funding type
        by_type = {}
        for funding in funding_rounds:
            funding_type = funding.get("funding_type", "Unknown")
            if funding_type not in by_type:
                by_type[funding_type] = {"count": 0, "total_amount": 0}
            by_type[funding_type]["count"] += 1
            if funding.get("amount"):
                by_type[funding_type]["total_amount"] += funding["amount"]

        return {
            "total_amount": total_amount,
            "round_count": round_count,
            "average_amount": average_amount,
            "by_type": by_type,
            "period_days": days
        }
