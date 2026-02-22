from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import and_, distinct, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.game import Game
from app.models.odds_snapshot import OddsSnapshot


async def capture_closing_lines(session: AsyncSession) -> int:
    now = datetime.now(UTC)
    started_game_ids = (
        await session.scalars(select(Game.id).where(Game.commence_time <= now, Game.completed.is_(False)))
    ).all()
    if not started_game_ids:
        return 0

    keys = (
        await session.execute(
            select(
                distinct(OddsSnapshot.game_id),
                OddsSnapshot.bookmaker,
                OddsSnapshot.market,
                OddsSnapshot.side,
            ).where(OddsSnapshot.game_id.in_(started_game_ids), OddsSnapshot.is_closing.is_(False))
        )
    ).all()

    marked = 0
    for game_id, bookmaker, market, side in keys:
        game = await session.scalar(select(Game).where(Game.id == game_id))
        if game is None:
            continue
        closing = await session.scalar(
            select(OddsSnapshot)
            .where(
                and_(
                    OddsSnapshot.game_id == game_id,
                    OddsSnapshot.bookmaker == bookmaker,
                    OddsSnapshot.market == market,
                    OddsSnapshot.side == side,
                    OddsSnapshot.snapshot_time < game.commence_time,
                )
            )
            .order_by(OddsSnapshot.snapshot_time.desc())
            .limit(1)
        )
        if closing is None or closing.is_closing:
            continue
        closing.is_closing = True
        marked += 1

    await session.commit()
    return marked
