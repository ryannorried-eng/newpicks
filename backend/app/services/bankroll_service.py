from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.game import Game
from app.models.pick import Pick

DEFAULT_STARTING_BANKROLL = 1000.0


async def get_current_bankroll(session: AsyncSession) -> dict:
    settled = (
        await session.scalars(select(Pick).where(Pick.outcome.in_(["win", "loss", "push"])))
    ).all()
    total_profit = sum(p.profit_loss or 0.0 for p in settled)
    total_wagered = sum(p.suggested_kelly_fraction or 0.0 for p in settled)
    current = DEFAULT_STARTING_BANKROLL + total_profit

    return {
        "starting_balance": DEFAULT_STARTING_BANKROLL,
        "current_balance": current,
        "total_wagered": total_wagered,
        "total_profit": total_profit,
        "roi_pct": (total_profit / total_wagered * 100.0) if total_wagered > 0 else 0.0,
        "num_bets": len(settled),
    }


async def get_kelly_suggestions(session: AsyncSession) -> list[dict]:
    bankroll = await get_current_bankroll(session)
    now = datetime.now(UTC)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)
    picks = (
        await session.scalars(
            select(Pick)
            .where(and_(Pick.pick_date >= start, Pick.pick_date < end))
            .order_by(Pick.ev_pct.desc())
        )
    ).all()

    out = []
    for pick in picks:
        game = await session.scalar(select(Game).where(Game.id == pick.game_id))
        matchup = f"{game.away_team} vs {game.home_team}" if game else "unknown"
        side = f"{pick.side} {pick.line}" if pick.line is not None else pick.side
        out.append(
            {
                "pick_id": pick.id,
                "game": matchup,
                "side": side,
                "kelly_fraction": pick.suggested_kelly_fraction,
                "current_bankroll": bankroll["current_balance"],
                "suggested_bet": bankroll["current_balance"] * (pick.suggested_kelly_fraction or 0.0),
            }
        )
    return out


async def get_bankroll_history(session: AsyncSession, days: int = 30) -> list[dict]:
    start = datetime.now(UTC).date() - timedelta(days=days - 1)
    rows = (
        await session.execute(
            select(func.date(Pick.created_at), func.sum(func.coalesce(Pick.profit_loss, 0.0)))
            .where(func.date(Pick.created_at) >= start, Pick.outcome.in_(["win", "loss", "push"]))
            .group_by(func.date(Pick.created_at))
            .order_by(func.date(Pick.created_at))
        )
    ).all()

    balance = DEFAULT_STARTING_BANKROLL
    history = []
    for d, p in rows:
        balance += float(p or 0.0)
        history.append({"date": str(d), "balance": balance})
    return history
