from __future__ import annotations

import asyncio
import os
from datetime import UTC, date, datetime
from typing import Any

import httpx


class NBAStatsClient:
    """Fetch team-level NBA stats for model features."""

    def __init__(self) -> None:
        self.base_url = "https://api.balldontlie.io/v1"
        self.api_key = os.environ.get("BALLDONTLIE_API_KEY")
        self._team_cache: dict[str, dict[str, Any]] = {}
        self._season_stats_cache: dict[int, list[dict[str, Any]]] = {}

    async def _request(self, endpoint: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        headers: dict[str, str] = {}
        if self.api_key:
            headers["Authorization"] = self.api_key

        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(f"{self.base_url}{endpoint}", params=params or {}, headers=headers)
            response.raise_for_status()
            return response.json()

    async def _get_teams(self) -> dict[str, dict[str, Any]]:
        if self._team_cache:
            return self._team_cache

        payload = await self._request("/teams")
        teams = payload.get("data", [])
        self._team_cache = {
            team["full_name"].lower(): team
            for team in teams
            if team.get("full_name")
        }
        return self._team_cache

    async def get_team_stats(self, season: int) -> list[dict]:
        if season in self._season_stats_cache:
            return self._season_stats_cache[season]

        teams = await self._get_teams()
        stats: list[dict[str, Any]] = []

        for team_name, team in teams.items():
            await asyncio.sleep(2.1)  # <= 30 req/min
            games_payload = await self._request(
                "/games",
                {
                    "seasons[]": season,
                    "team_ids[]": team["id"],
                    "per_page": 100,
                },
            )
            games = games_payload.get("data", [])
            if not games:
                continue

            wins = 0
            losses = 0
            points_for = 0
            points_against = 0
            for game in games:
                is_home = game.get("home_team", {}).get("id") == team["id"]
                team_score = game.get("home_team_score", 0) if is_home else game.get("visitor_team_score", 0)
                opp_score = game.get("visitor_team_score", 0) if is_home else game.get("home_team_score", 0)
                points_for += team_score
                points_against += opp_score
                if team_score > opp_score:
                    wins += 1
                else:
                    losses += 1

            played = max(wins + losses, 1)
            off_rating = (points_for / played) * 1.02
            def_rating = (points_against / played) * 1.02
            net = off_rating - def_rating
            pace = 98.0 + (net * 0.2)

            stats.append(
                {
                    "team_id": team["id"],
                    "team_name": team["full_name"],
                    "abbreviation": team["abbreviation"],
                    "wins": wins,
                    "losses": losses,
                    "offensive_rating": round(off_rating, 3),
                    "defensive_rating": round(def_rating, 3),
                    "net_rating": round(net, 3),
                    "pace": round(pace, 3),
                    "true_shooting_pct": 0.56,
                    "rebound_pct": 0.5,
                    "turnover_pct": 0.135,
                    "assist_pct": 0.61,
                }
            )

        self._season_stats_cache[season] = stats
        return stats

    async def get_recent_games(self, team_id: int, n_games: int = 10) -> list[dict]:
        payload = await self._request(
            "/games",
            {
                "team_ids[]": team_id,
                "per_page": n_games,
            },
        )
        games = payload.get("data", [])
        recent: list[dict[str, Any]] = []

        for game in games[:n_games]:
            is_home = game.get("home_team", {}).get("id") == team_id
            opp_name = game.get("visitor_team", {}).get("full_name") if is_home else game.get("home_team", {}).get("full_name")
            team_score = game.get("home_team_score", 0) if is_home else game.get("visitor_team_score", 0)
            opp_score = game.get("visitor_team_score", 0) if is_home else game.get("home_team_score", 0)
            recent.append(
                {
                    "date": game.get("date", "")[:10],
                    "opponent": opp_name or "Unknown",
                    "home": is_home,
                    "score": team_score,
                    "opponent_score": opp_score,
                    "win": team_score > opp_score,
                }
            )

        return recent

    async def get_schedule_context(self, team_id: int, game_date: date) -> dict:
        payload = await self._request(
            "/games",
            {
                "team_ids[]": team_id,
                "dates[]": game_date.isoformat(),
                "per_page": 1,
            },
        )
        is_home = False
        game_day = payload.get("data", [])
        if game_day:
            game = game_day[0]
            is_home = game.get("home_team", {}).get("id") == team_id

        recent_payload = await self._request("/games", {"team_ids[]": team_id, "per_page": 20})
        games = recent_payload.get("data", [])
        parsed_dates: list[datetime] = []
        for game in games:
            d = game.get("date")
            if not d:
                continue
            parsed_dates.append(datetime.fromisoformat(d.replace("Z", "+00:00")).astimezone(UTC))

        parsed_dates.sort(reverse=True)
        prior_games = [d for d in parsed_dates if d.date() < game_date]
        rest_days = (game_date - prior_games[0].date()).days if prior_games else 3
        games_in_last_7 = sum(1 for d in prior_games if (game_date - d.date()).days <= 7)

        return {
            "rest_days": max(rest_days, 0),
            "is_back_to_back": rest_days <= 1,
            "games_in_last_7": games_in_last_7,
            "is_home": is_home,
            "travel_distance_est": 0 if is_home else 250,
        }
