import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


def normalize_str(s: str | None) -> str:
    """Normalize strings for robust comparisons."""
    if s is None:
        return ""
    return re.sub(r"\s+", " ", s.strip().lower())


def resolve_side(side: str | None, home_team: str | None, away_team: str | None) -> str | None:
    """Map side to canonical home/away when possible."""
    normalized_side = normalize_str(side)
    normalized_home = normalize_str(home_team)
    normalized_away = normalize_str(away_team)

    if normalized_side == "home":
        return "home"
    if normalized_side == "away":
        return "away"

    if normalized_side and normalized_home and normalized_side == normalized_home:
        return "home"
    if normalized_side and normalized_away and normalized_side == normalized_away:
        return "away"

    if normalized_side:
        logger.warning(
            "Could not resolve side '%s' for home='%s' away='%s'",
            side,
            home_team,
            away_team,
        )
    return None


def normalize_team_name(team: str | None) -> str | None:
    """Normalized team-side text for matching/debugging (not display)."""
    normalized = normalize_str(team)
    return normalized or None


def format_live_odds_rows(rows: list[tuple[Any, str | None, str | None]]) -> list[dict]:
    """Backwards-compatible row formatter used by tests and API composition."""
    payload: list[dict] = []

    for snapshot, home_team, away_team in rows:
        if snapshot.market in {"h2h", "spreads"}:
            canonical_side = resolve_side(snapshot.side, home_team, away_team)
            normalized_team = normalize_team_name(snapshot.side)
        else:
            canonical_side = None
            normalized_team = None

        payload.append(
            {
                "game_id": snapshot.game_id,
                "home_team": home_team,
                "away_team": away_team,
                "sport_key": snapshot.sport_key,
                "bookmaker": snapshot.bookmaker,
                "market": snapshot.market,
                "side": snapshot.side,
                "canonical_side": canonical_side,
                "normalized_team": normalized_team,
                "odds": snapshot.odds,
                "line": snapshot.line,
                "snapshot_time": snapshot.snapshot_time.isoformat() if snapshot.snapshot_time else None,
            }
        )

    return payload
