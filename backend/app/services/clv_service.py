from __future__ import annotations

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.odds_snapshot import OddsSnapshot
from app.models.pick import Pick
from app.utils.odds_math import american_to_implied_prob

SHARP_BOOKS = {"pinnacle", "circa", "bookmaker", "betcris"}


async def calculate_clv_for_pick(pick: Pick, session: AsyncSession) -> dict:
    snapshots = (
        await session.scalars(
            select(OddsSnapshot).where(
                and_(
                    OddsSnapshot.game_id == pick.game_id,
                    OddsSnapshot.market == pick.market,
                    OddsSnapshot.side == pick.side,
                    OddsSnapshot.is_closing.is_(True),
                )
            )
        )
    ).all()
    if not snapshots:
        return {"updated": False}

    weighted_sum = 0.0
    weight_total = 0.0
    for snap in snapshots:
        weight = 2.0 if snap.bookmaker in SHARP_BOOKS else 1.0
        weighted_sum += snap.no_vig_prob * weight
        weight_total += weight
    closing_consensus = weighted_sum / weight_total if weight_total else None

    book_snap = next((s for s in snapshots if s.bookmaker == pick.best_book), None)
    pick_prob = american_to_implied_prob(pick.odds_american)

    pick.market_clv = (closing_consensus - pick_prob) if closing_consensus is not None else None
    pick.book_clv = (book_snap.no_vig_prob - pick_prob) if book_snap else None
    await session.commit()
    return {"updated": True, "market_clv": pick.market_clv, "book_clv": pick.book_clv}


async def calculate_all_pending_clv(session: AsyncSession) -> int:
    picks = (
        await session.scalars(
            select(Pick).where(
                Pick.outcome.in_(["win", "loss", "push"]),
                Pick.market_clv.is_(None),
                Pick.book_clv.is_(None),
            )
        )
    ).all()
    updated = 0
    for pick in picks:
        result = await calculate_clv_for_pick(pick, session)
        if result.get("updated"):
            updated += 1
    return updated
