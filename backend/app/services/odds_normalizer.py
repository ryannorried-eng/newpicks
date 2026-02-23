import logging

logger = logging.getLogger(__name__)


def _normalize(value: str | None) -> str:
    return (value or "").strip().lower()


def resolve_side(side: str | None, home_team: str | None, away_team: str | None) -> str | None:
    normalized_side = _normalize(side)
    normalized_home = _normalize(home_team)
    normalized_away = _normalize(away_team)

    if normalized_side == "home" or (normalized_home and normalized_side == normalized_home):
        return "home"
    if normalized_side == "away" or (normalized_away and normalized_side == normalized_away):
        return "away"

    if normalized_side:
        logger.warning(
            "Could not resolve side '%s' for home='%s' away='%s'",
            side,
            home_team,
            away_team,
        )

    return None


def normalize_team(side: str | None, home_team: str | None, away_team: str | None) -> str | None:
    canonical_side = resolve_side(side, home_team, away_team)
    if canonical_side == "home":
        return home_team
    if canonical_side == "away":
        return away_team
    return None


def format_live_odds_rows(rows: list[tuple[object, str | None, str | None]]) -> list[dict]:
    payload: list[dict] = []
    for snapshot, home_team, away_team in rows:
        if snapshot.market in {"h2h", "spreads"}:
            canonical_side = resolve_side(snapshot.side, home_team, away_team)
            normalized_team = normalize_team(snapshot.side, home_team, away_team)
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
