from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models.game import Game
from app.models.pick import Pick
from app.schemas.picks import PickResponse
from app.tasks.generate_picks import run_generate_picks
from app.tasks.generate_parlays import run_generate_parlays

router = APIRouter(prefix="/picks", tags=["picks"])


async def _serialize_pick(session: AsyncSession, pick: Pick) -> PickResponse:
    game = await session.scalar(select(Game).where(Game.id == pick.game_id))
    return PickResponse(
        id=pick.id,
        game_id=pick.game_id,
        sport_key=pick.sport_key,
        home_team=game.home_team if game else "",
        away_team=game.away_team if game else "",
        commence_time=game.commence_time if game else pick.created_at,
        market=pick.market,
        side=pick.side,
        line=pick.line,
        odds_american=pick.odds_american,
        best_book=pick.best_book,
        fair_prob=pick.fair_prob,
        prob_source=pick.prob_source,
        implied_prob=pick.implied_prob,
        ev_pct=pick.ev_pct,
        composite_score=pick.composite_score,
        confidence_tier=pick.confidence_tier,
        signals=pick.signals,
        data_quality=pick.data_quality,
        suggested_kelly_fraction=pick.suggested_kelly_fraction,
        outcome=pick.outcome,
        market_clv=pick.market_clv,
        book_clv=pick.book_clv,
        created_at=pick.created_at,
    )


@router.post("/generate")
async def trigger_generate_picks() -> dict[str, int | str]:
    summary = await run_generate_picks()
    if int(summary.get("picks_created", 0)) > 0:
        await run_generate_parlays()
    return summary


@router.get("/live", response_model=list[PickResponse])
async def get_live_picks(session: AsyncSession = Depends(get_session)) -> list[PickResponse]:
    now = datetime.now(UTC)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    picks = (
        await session.scalars(
            select(Pick).where(Pick.pick_date >= start).order_by(Pick.ev_pct.desc())
        )
    ).all()
    return [await _serialize_pick(session, p) for p in picks]


@router.get("/today", response_model=list[PickResponse])
async def get_today_picks(session: AsyncSession = Depends(get_session)) -> list[PickResponse]:
    now = datetime.now(UTC)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)
    picks = (
        await session.scalars(
            select(Pick).where(and_(Pick.pick_date >= start, Pick.pick_date < end)).order_by(Pick.ev_pct.desc())
        )
    ).all()
    return [await _serialize_pick(session, p) for p in picks]


@router.get("/history", response_model=list[PickResponse])
async def get_pick_history(
    sport: str | None = Query(default=None),
    market: str | None = Query(default=None),
    confidence: str | None = Query(default=None),
    start_date: datetime | None = Query(default=None),
    end_date: datetime | None = Query(default=None),
    limit: int = Query(default=50, le=200),
    session: AsyncSession = Depends(get_session),
) -> list[PickResponse]:
    stmt = select(Pick)
    if sport:
        stmt = stmt.where(Pick.sport_key == sport)
    if market:
        stmt = stmt.where(Pick.market == market)
    if confidence:
        stmt = stmt.where(Pick.confidence_tier == confidence)
    if start_date:
        stmt = stmt.where(Pick.created_at >= start_date)
    if end_date:
        stmt = stmt.where(Pick.created_at <= end_date)

    picks = (await session.scalars(stmt.order_by(Pick.created_at.desc()).limit(limit))).all()
    return [await _serialize_pick(session, p) for p in picks]


@router.get("/{pick_id}", response_model=PickResponse)
async def get_pick_detail(pick_id: int, session: AsyncSession = Depends(get_session)) -> PickResponse:
    pick = await session.scalar(select(Pick).where(Pick.id == pick_id))
    if pick is None:
        raise HTTPException(status_code=404, detail="Pick not found")
    return await _serialize_pick(session, pick)
