from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.services.bankroll_service import get_bankroll_history, get_current_bankroll, get_kelly_suggestions

router = APIRouter(prefix="/bankroll", tags=["bankroll"])


@router.get("/current")
async def current_bankroll(session: AsyncSession = Depends(get_session)) -> dict:
    return await get_current_bankroll(session)


@router.get("/kelly-suggestions")
async def kelly_suggestions(session: AsyncSession = Depends(get_session)) -> list[dict]:
    return await get_kelly_suggestions(session)


@router.get("/history")
async def bankroll_history(days: int = Query(default=30, ge=1, le=365), session: AsyncSession = Depends(get_session)) -> list[dict]:
    return await get_bankroll_history(session, days=days)
