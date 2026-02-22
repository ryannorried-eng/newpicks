from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends

from app.database import get_session
from app.models.odds_snapshot import OddsSnapshot

router = APIRouter(prefix="/odds", tags=["odds"])


@router.get("/live")
async def live_odds(session: AsyncSession = Depends(get_session)) -> list[dict]:
    rows = (await session.scalars(select(OddsSnapshot).order_by(OddsSnapshot.snapshot_time.desc()).limit(100))).all()
    return [
        {
            "game_id": r.game_id,
            "sport_key": r.sport_key,
            "bookmaker": r.bookmaker,
            "market": r.market,
            "side": r.side,
            "odds": r.odds,
            "line": r.line,
            "snapshot_time": r.snapshot_time.isoformat() if r.snapshot_time else None,
        }
        for r in rows
    ]
