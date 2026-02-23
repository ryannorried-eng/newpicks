from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends

from app.database import get_session
from app.models.game import Game
from app.models.odds_snapshot import OddsSnapshot
from app.services.odds_normalizer import format_live_odds_rows

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
    return format_live_odds_rows(rows)
