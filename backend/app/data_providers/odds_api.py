from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

from app.config import settings


@dataclass
class OddsAPIResult:
    data: list[dict[str, Any]]
    requests_remaining: int | None


class OddsAPIClient:
    def __init__(self) -> None:
        self.base_url = settings.odds_api_base_url.rstrip("/")
        self.api_key = settings.odds_api_key
        self.requests_remaining: int | None = None

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> OddsAPIResult:
        if not self.api_key:
            return OddsAPIResult(data=[], requests_remaining=self.requests_remaining)
        params = params or {}
        params["apiKey"] = self.api_key
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(f"{self.base_url}/{path.lstrip('/')}", params=params)
            response.raise_for_status()
            remaining = response.headers.get("x-requests-remaining")
            self.requests_remaining = int(remaining) if remaining and remaining.isdigit() else self.requests_remaining
            data = response.json()
            if isinstance(data, list):
                return OddsAPIResult(data=data, requests_remaining=self.requests_remaining)
            return OddsAPIResult(data=[data], requests_remaining=self.requests_remaining)

    async def get_sports(self) -> OddsAPIResult:
        result = await self._get("sports")
        if result.data:
            return result
        return OddsAPIResult(
            data=[
                {"key": "basketball_nba", "title": "NBA", "active": True},
                {"key": "americanfootball_nfl", "title": "NFL", "active": True},
            ],
            requests_remaining=result.requests_remaining,
        )

    async def get_odds(
        self,
        sport: str,
        regions: str = "us",
        markets: str = "h2h,spreads,totals",
        bookmakers: str | None = None,
    ) -> OddsAPIResult:
        params: dict[str, Any] = {"regions": regions, "markets": markets, "oddsFormat": "american"}
        if bookmakers:
            params["bookmakers"] = bookmakers
        result = await self._get(f"sports/{sport}/odds", params=params)
        if result.data:
            return result
        now = datetime.now(UTC)
        return OddsAPIResult(
            data=[
                {
                    "id": f"demo-{sport}-001",
                    "commence_time": (now + timedelta(hours=2)).isoformat().replace("+00:00", "Z"),
                    "home_team": "Home",
                    "away_team": "Away",
                    "bookmakers": [
                        {
                            "key": "draftkings",
                            "markets": [
                                {"key": "h2h", "outcomes": [{"name": "Home", "price": -110}, {"name": "Away", "price": -105}]}
                            ],
                        }
                    ],
                }
            ],
            requests_remaining=result.requests_remaining,
        )

    async def get_scores(self, sport: str) -> OddsAPIResult:
        return await self._get(f"sports/{sport}/scores", params={"oddsFormat": "american"})
