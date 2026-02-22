from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from datetime import date

from app.data_providers.nba_stats import NBAStatsClient, normalize_team_name, team_last_word

logger = logging.getLogger(__name__)


@dataclass
class GameFeatures:
    home_off_rating: float
    home_def_rating: float
    home_net_rating: float
    away_off_rating: float
    away_def_rating: float
    away_net_rating: float
    home_pace: float
    away_pace: float
    expected_pace: float
    home_last10_win_pct: float
    away_last10_win_pct: float
    home_last10_net_rating: float
    away_last10_net_rating: float
    home_rest_days: int
    away_rest_days: int
    home_is_b2b: bool
    away_is_b2b: bool
    home_games_last_7: int
    away_games_last_7: int
    net_rating_diff: float
    pace_diff: float
    off_vs_def_mismatch: float
    def_vs_off_mismatch: float
    is_home: float = 1.0


def _resolve_team_stats(team_name: str, by_name: dict[str, dict], by_last_word: dict[str, dict]) -> dict | None:
    normalized = normalize_team_name(team_name)
    direct = by_name.get(normalized.lower())
    if direct is not None:
        return direct
    return by_last_word.get(team_last_word(normalized))


async def build_game_features(home_team: str, away_team: str, game_date: date, nba_client: NBAStatsClient) -> GameFeatures:
    season = game_date.year
    season_stats = await nba_client.get_team_stats(season)
    if not season_stats:
        raise ValueError("No team stats available")

    by_name = {normalize_team_name(team["team_name"]).lower(): team for team in season_stats}
    by_last_word = {team_last_word(team["team_name"]): team for team in season_stats}
    logger.info(
        "Matching teams for features home='%s' away='%s'; available_stats_teams=%s",
        home_team,
        away_team,
        sorted(by_name.keys()),
    )

    home = _resolve_team_stats(home_team, by_name, by_last_word)
    away = _resolve_team_stats(away_team, by_name, by_last_word)
    if home is None or away is None:
        raise ValueError(f"Missing team stats for {home_team} vs {away_team}")

    home_recent = await nba_client.get_recent_games(home["team_id"], n_games=10)
    away_recent = await nba_client.get_recent_games(away["team_id"], n_games=10)

    home_ctx = await nba_client.get_schedule_context(home["team_id"], game_date)
    away_ctx = await nba_client.get_schedule_context(away["team_id"], game_date)

    def recent_metrics(games: list[dict]) -> tuple[float, float]:
        if not games:
            return 0.5, 0.0
        wins = sum(1 for g in games if g["win"])
        net = sum((g["score"] - g["opponent_score"]) for g in games) / len(games)
        return wins / len(games), net

    home_win_pct, home_last10_net = recent_metrics(home_recent)
    away_win_pct, away_last10_net = recent_metrics(away_recent)

    return GameFeatures(
        home_off_rating=home["offensive_rating"],
        home_def_rating=home["defensive_rating"],
        home_net_rating=home["net_rating"],
        away_off_rating=away["offensive_rating"],
        away_def_rating=away["defensive_rating"],
        away_net_rating=away["net_rating"],
        home_pace=home["pace"],
        away_pace=away["pace"],
        expected_pace=(home["pace"] + away["pace"]) / 2,
        home_last10_win_pct=home_win_pct,
        away_last10_win_pct=away_win_pct,
        home_last10_net_rating=home_last10_net,
        away_last10_net_rating=away_last10_net,
        home_rest_days=home_ctx["rest_days"],
        away_rest_days=away_ctx["rest_days"],
        home_is_b2b=home_ctx["is_back_to_back"],
        away_is_b2b=away_ctx["is_back_to_back"],
        home_games_last_7=home_ctx["games_in_last_7"],
        away_games_last_7=away_ctx["games_in_last_7"],
        net_rating_diff=home["net_rating"] - away["net_rating"],
        pace_diff=home["pace"] - away["pace"],
        off_vs_def_mismatch=home["offensive_rating"] - away["defensive_rating"],
        def_vs_off_mismatch=away["offensive_rating"] - home["defensive_rating"],
    )


def features_to_array(features: GameFeatures) -> list[float]:
    return [
        features.home_off_rating,
        features.home_def_rating,
        features.home_net_rating,
        features.away_off_rating,
        features.away_def_rating,
        features.away_net_rating,
        features.home_pace,
        features.away_pace,
        features.expected_pace,
        features.home_last10_win_pct,
        features.away_last10_win_pct,
        features.home_last10_net_rating,
        features.away_last10_net_rating,
        float(features.home_rest_days),
        float(features.away_rest_days),
        float(features.home_is_b2b),
        float(features.away_is_b2b),
        float(features.home_games_last_7),
        float(features.away_games_last_7),
        features.net_rating_diff,
        features.pace_diff,
        features.off_vs_def_mismatch,
        features.def_vs_off_mismatch,
        features.is_home,
    ]


def features_to_dict(features: GameFeatures) -> dict[str, float | int | bool]:
    return asdict(features)


FEATURE_NAMES = [
    "home_off_rating", "home_def_rating", "home_net_rating",
    "away_off_rating", "away_def_rating", "away_net_rating",
    "home_pace", "away_pace", "expected_pace",
    "home_last10_win_pct", "away_last10_win_pct",
    "home_last10_net_rating", "away_last10_net_rating",
    "home_rest_days", "away_rest_days",
    "home_is_b2b", "away_is_b2b",
    "home_games_last_7", "away_games_last_7",
    "net_rating_diff", "pace_diff",
    "off_vs_def_mismatch", "def_vs_off_mismatch",
    "is_home",
]
