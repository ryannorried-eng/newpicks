from __future__ import annotations

from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models.game import Game
from app.models.parlay import Parlay, ParlayLeg
from app.models.pick import Pick
from app.schemas.parlays import ParlayBuildRequest, ParlayBuildResponse, ParlayLegResponse, ParlayResponse
from app.schemas.picks import PickResponse
from app.services.parlay_service import build_custom_parlay, generate_daily_parlays
from app.tasks.generate_parlays import run_generate_parlays

router = APIRouter(prefix="/parlays", tags=["parlays"])


async def _pick_response(session: AsyncSession, pick: Pick) -> PickResponse:
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


async def _serialize_parlay(session: AsyncSession, parlay: Parlay) -> ParlayResponse:
    leg_rows = (
        await session.scalars(select(ParlayLeg).where(ParlayLeg.parlay_id == parlay.id).order_by(ParlayLeg.leg_order))
    ).all()
    legs: list[ParlayLegResponse] = []
    for leg in leg_rows:
        pick = await session.scalar(select(Pick).where(Pick.id == leg.pick_id))
        if pick is None:
            continue
        legs.append(
            ParlayLegResponse(
                id=leg.id,
                pick_id=leg.pick_id,
                leg_order=leg.leg_order,
                result=leg.result,
                pick=await _pick_response(session, pick),
            )
        )

    return ParlayResponse(
        id=parlay.id,
        risk_level=parlay.risk_level,
        num_legs=parlay.num_legs,
        combined_odds_american=parlay.combined_odds_american,
        combined_odds_decimal=parlay.combined_odds_decimal,
        combined_ev_pct=parlay.combined_ev_pct,
        combined_fair_prob=parlay.combined_fair_prob,
        correlation_score=parlay.correlation_score,
        suggested_kelly_fraction=parlay.suggested_kelly_fraction,
        outcome=parlay.outcome,
        profit_loss=parlay.profit_loss,
        created_at=parlay.created_at,
        legs=legs,
    )


@router.get("/today", response_model=list[ParlayResponse])
async def get_today_parlays(session: AsyncSession = Depends(get_session)) -> list[ParlayResponse]:
    today = datetime.utcnow().date()
    rows = (
        await session.scalars(select(Parlay).where(Parlay.pick_date == today).order_by(Parlay.risk_level, Parlay.combined_ev_pct.desc()))
    ).all()
    return [await _serialize_parlay(session, p) for p in rows]


@router.post("/generate")
async def trigger_generate_parlays(session: AsyncSession = Depends(get_session)) -> dict:
    await run_generate_parlays()
    today = datetime.utcnow().date()
    rows = (await session.scalars(select(Parlay).where(Parlay.pick_date == today))).all()
    summary = {"conservative": 0, "moderate": 0, "aggressive": 0}
    for p in rows:
        summary[p.risk_level] = summary.get(p.risk_level, 0) + 1
    return {"generated": summary}


@router.post("/build", response_model=ParlayBuildResponse)
async def build_parlay(request: ParlayBuildRequest, session: AsyncSession = Depends(get_session)) -> ParlayBuildResponse:
    result = await build_custom_parlay(session, request.pick_ids)
    return ParlayBuildResponse(**result)


@router.get("/history", response_model=list[ParlayResponse])
async def parlay_history(
    risk_level: str | None = Query(default=None),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    limit: int = Query(default=50, le=200),
    session: AsyncSession = Depends(get_session),
) -> list[ParlayResponse]:
    stmt = select(Parlay)
    if risk_level:
        stmt = stmt.where(Parlay.risk_level == risk_level)
    if start_date:
        stmt = stmt.where(Parlay.pick_date >= start_date)
    if end_date:
        stmt = stmt.where(Parlay.pick_date <= end_date)

    rows = (await session.scalars(stmt.order_by(Parlay.created_at.desc()).limit(limit))).all()
    return [await _serialize_parlay(session, p) for p in rows]
