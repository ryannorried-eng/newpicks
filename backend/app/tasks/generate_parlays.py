from __future__ import annotations

from sqlalchemy import text

from app.database import AsyncSessionLocal
from app.services.parlay_service import generate_daily_parlays

ADVISORY_LOCK_KEY = 927411


async def run_generate_parlays() -> int:
    async with AsyncSessionLocal() as session:
        lock = await session.scalar(text("SELECT pg_try_advisory_lock(:key)"), {"key": ADVISORY_LOCK_KEY})
        if not lock:
            return 0
        try:
            parlays = await generate_daily_parlays(session)
            return len(parlays)
        finally:
            await session.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": ADVISORY_LOCK_KEY})
            await session.commit()
