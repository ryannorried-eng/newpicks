from __future__ import annotations

import logging
import re
from typing import Literal

logger = logging.getLogger(__name__)

_TEAM_NAME_ALIASES: dict[str, str] = {
    "la clippers": "Los Angeles Clippers",
    "los angeles clippers": "Los Angeles Clippers",
    "la lakers": "Los Angeles Lakers",
    "los angeles lakers": "Los Angeles Lakers",
}


def normalize_str(value: str | None) -> str:
    compact = re.sub(r"\s+", " ", str(value or "").strip())
    return compact.lower()


def normalize_team_name(team_name: str | None) -> str:
    cleaned = re.sub(r"\s+", " ", str(team_name or "").strip())
    if not cleaned:
        return ""
    return _TEAM_NAME_ALIASES.get(cleaned.lower(), cleaned)


def normalize_pick_side_label(side: str | None) -> str:
    normalized = normalize_str(side)
    if normalized == "home":
        return "home"
    if normalized == "away":
        return "away"
    if normalized == "over":
        return "over"
    if normalized == "under":
        return "under"
    return str(side or "").strip()


def resolve_side(
    side: str | None,
    home_team: str | None,
    away_team: str | None,
    *,
    snapshot_id: int | None = None,
) -> Literal["home", "away"] | None:
    normalized_side = normalize_str(side)
    if normalized_side == "home":
        return "home"
    if normalized_side == "away":
        return "away"

    normalized_home = normalize_str(home_team)
    normalized_away = normalize_str(away_team)

    if normalized_side and normalized_side == normalized_home:
        return "home"
    if normalized_side and normalized_side == normalized_away:
        return "away"

    alias_side = normalize_str(normalize_team_name(side))
    alias_home = normalize_str(normalize_team_name(home_team))
    alias_away = normalize_str(normalize_team_name(away_team))

    if alias_side and alias_side == alias_home:
        return "home"
    if alias_side and alias_side == alias_away:
        return "away"

    logger.warning(
        "Could not resolve odds snapshot side",
        extra={
            "snapshot_id": snapshot_id,
            "side": side,
            "home_team": home_team,
            "away_team": away_team,
        },
    )
    return None
