from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.services.performance_service import get_daily_performance, get_performance_summary, get_roi_over_time, summary_to_dict

router = APIRouter(prefix="/performance", tags=["performance"])


@router.get("/summary")
async def performance_summary(
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    sport_key: str | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
) -> dict:
    summary = await get_performance_summary(session, start_date=start_date, end_date=end_date, sport_key=sport_key)
    return summary_to_dict(summary)


@router.get("/daily")
async def performance_daily(days: int = Query(default=30, ge=1, le=365), session: AsyncSession = Depends(get_session)) -> list[dict]:
    return await get_daily_performance(session, days=days)


@router.get("/roi-curve")
async def roi_curve(session: AsyncSession = Depends(get_session)) -> list[dict]:
    return await get_roi_over_time(session)


@router.get("/by-sport")
async def by_sport(session: AsyncSession = Depends(get_session)) -> dict:
    summary = await get_performance_summary(session)
    return summary.by_sport


@router.get("/by-market")
async def by_market(session: AsyncSession = Depends(get_session)) -> dict:
    summary = await get_performance_summary(session)
    return summary.by_market


@router.get("/by-tier")
async def by_tier(session: AsyncSession = Depends(get_session)) -> dict:
    summary = await get_performance_summary(session)
    return {
        "high": summary.high_confidence,
        "medium": summary.medium_confidence,
        "low": summary.low_confidence,
    }
