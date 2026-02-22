from __future__ import annotations

import asyncio
from datetime import UTC, date, datetime
from typing import Any

import pandas as pd
from nba_api.stats.endpoints import leaguegamefinder, leaguestandings, teamestimatedmetrics
from nba_api.stats.library.parameters import SeasonTypeAllStar
from nba_api.stats.static import teams


class NBAStatsClient:
    """Fetch team-level NBA stats for model features via nba_api."""

    REQUEST_DELAY_S = 0.6

    def __init__(self) -> None:
        self._team_cache: dict[int, dict[str, Any]] = {}
        self._team_name_cache: dict[str, dict[str, Any]] = {}
        self._season_stats_cache: dict[int, list[dict[str, Any]]] = {}

    async def _pace(self) -> None:
        await asyncio.sleep(self.REQUEST_DELAY_S)

    async def _load_teams(self) -> dict[int, dict[str, Any]]:
        if self._team_cache:
            return self._team_cache

        static_teams = await asyncio.to_thread(teams.get_teams)
        cache: dict[int, dict[str, Any]] = {}
        by_name: dict[str, dict[str, Any]] = {}
        for team in static_teams:
            tid = int(team["id"])
            full_name = str(team["full_name"])
            info = {
                "team_id": tid,
                "team_name": full_name,
                "abbreviation": str(team["abbreviation"]),
                "city": str(team["city"]),
                "nickname": str(team["nickname"]),
            }
            cache[tid] = info
            by_name[full_name.lower()] = info

        self._team_cache = cache
        self._team_name_cache = by_name
        return self._team_cache

    async def _season_str(self, season: int) -> str:
        # nba_api expects season like "2024-25"
        return f"{season}-{str(season + 1)[-2:]}"

    async def _get_team_games_df(self, team_id: int, season: int | None = None) -> pd.DataFrame:
        params: dict[str, Any] = {
            "team_id_nullable": team_id,
            "season_type_nullable": SeasonTypeAllStar.regular,
        }
        if season is not None:
            params["season_nullable"] = await self._season_str(season)

        endpoint = await asyncio.to_thread(leaguegamefinder.LeagueGameFinder, **params)
        await self._pace()
        frames = endpoint.get_data_frames()
        if not frames:
            return pd.DataFrame()

        df = frames[0].copy()
        if "GAME_DATE" in df.columns:
            df["GAME_DATE"] = pd.to_datetime(df["GAME_DATE"], utc=True, errors="coerce")
        return df

    async def get_team_stats(self, season: int) -> list[dict]:
        if season in self._season_stats_cache:
            return self._season_stats_cache[season]

        await self._load_teams()
        season_str = await self._season_str(season)

        standings_ep = await asyncio.to_thread(
            leaguestandings.LeagueStandings,
            season=season_str,
            season_type=SeasonTypeAllStar.regular,
        )
        await self._pace()
        standings_df = standings_ep.get_data_frames()[0]

        metrics_ep = await asyncio.to_thread(
            teamestimatedmetrics.TeamEstimatedMetrics,
            season=season_str,
            season_type=SeasonTypeAllStar.regular,
        )
        await self._pace()
        metrics_df = metrics_ep.get_data_frames()[0]

        metrics_by_team = {
            int(row["TEAM_ID"]): row
            for _, row in metrics_df.iterrows()
            if pd.notna(row.get("TEAM_ID"))
        }

        stats: list[dict[str, Any]] = []
        for _, row in standings_df.iterrows():
            team_id = int(row["TeamID"])
            team_info = self._team_cache.get(team_id)
            if not team_info:
                continue
            m = metrics_by_team.get(team_id)
            off = float(m["E_OFF_RATING"]) if m is not None and pd.notna(m.get("E_OFF_RATING")) else 110.0
            deff = float(m["E_DEF_RATING"]) if m is not None and pd.notna(m.get("E_DEF_RATING")) else 110.0
            net = float(m["E_NET_RATING"]) if m is not None and pd.notna(m.get("E_NET_RATING")) else off - deff
            pace = float(m["E_PACE"]) if m is not None and pd.notna(m.get("E_PACE")) else 99.0

            stats.append(
                {
                    "team_id": team_id,
                    "team_name": team_info["team_name"],
                    "abbreviation": team_info["abbreviation"],
                    "wins": int(row.get("WINS", 0)),
                    "losses": int(row.get("LOSSES", 0)),
                    "offensive_rating": round(off, 3),
                    "defensive_rating": round(deff, 3),
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
        await self._load_teams()
        df = await self._get_team_games_df(team_id)
        if df.empty:
            return []

        df = df.sort_values("GAME_DATE", ascending=False).head(n_games)
        recent: list[dict[str, Any]] = []
        for _, row in df.iterrows():
            matchup = str(row.get("MATCHUP", ""))
            is_home = " vs. " in matchup
            opp_abbr = matchup.split()[-1] if matchup else ""
            opp_team = next((t["team_name"] for t in self._team_cache.values() if t["abbreviation"] == opp_abbr), opp_abbr or "Unknown")
            pts = int(row.get("PTS", 0) or 0)
            plus_minus = float(row.get("PLUS_MINUS", 0.0) or 0.0)
            opp_pts = int(round(pts - plus_minus))
            game_date = row.get("GAME_DATE")
            date_str = game_date.date().isoformat() if pd.notna(game_date) else ""

            recent.append(
                {
                    "date": date_str,
                    "opponent": opp_team,
                    "home": is_home,
                    "score": pts,
                    "opponent_score": opp_pts,
                    "win": str(row.get("WL", "")).upper() == "W",
                }
            )

        return recent

    async def get_schedule_context(self, team_id: int, game_date: date) -> dict:
        df = await self._get_team_games_df(team_id)
        if df.empty:
            return {
                "rest_days": 3,
                "is_back_to_back": False,
                "games_in_last_7": 0,
                "is_home": True,
                "travel_distance_est": 0,
            }

        target_dt = datetime.combine(game_date, datetime.min.time(), tzinfo=UTC)
        prior = df[df["GAME_DATE"] < target_dt].sort_values("GAME_DATE", ascending=False)

        rest_days = 3
        games_in_last_7 = 0
        if not prior.empty:
            last_dt = prior.iloc[0]["GAME_DATE"]
            rest_days = max((target_dt.date() - last_dt.date()).days, 0)
            games_in_last_7 = int((prior["GAME_DATE"] >= (target_dt - pd.Timedelta(days=7))).sum())

        same_day = df[df["GAME_DATE"].dt.date == game_date]
        is_home = True
        if not same_day.empty:
            matchup = str(same_day.iloc[0].get("MATCHUP", ""))
            is_home = " vs. " in matchup

        return {
            "rest_days": rest_days,
            "is_back_to_back": rest_days <= 1,
            "games_in_last_7": games_in_last_7,
            "is_home": is_home,
            "travel_distance_est": 0 if is_home else 250,
        }
