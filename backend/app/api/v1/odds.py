from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends

from app.database import get_session
from app.models.game import Game
from app.models.odds_snapshot import OddsSnapshot
from app.services.odds_normalizer import normalize_team_name, resolve_side

router = APIRouter(prefix="/odds", tags=["odds"])


@router.get("/live")
async def live_odds(session: AsyncSession = Depends(get_session)) -> list[dict]:
    rows = (
        await session.execute(
            select(OddsSnapshot, Game.home_team, Game.away_team)
            .outerjoin(Game, OddsSnapshot.game_id == Game.id)
            .order_by(OddsSnapshot.snapshot_time.desc())
            .limit(100)
        )
    ).all()

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
