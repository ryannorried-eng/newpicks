from __future__ import annotations

from sqlalchemy import text

from app.database import AsyncSessionLocal
from app.services.pick_service import update_closing_lines_for_open_picks

ADVISORY_LOCK_KEY = 927414


async def run_update_pick_clv() -> int:
    async with AsyncSessionLocal() as session:
        lock = await session.scalar(text("SELECT pg_try_advisory_lock(:key)"), {"key": ADVISORY_LOCK_KEY})
        if not lock:
            return 0
        try:
            return await update_closing_lines_for_open_picks(session)
        finally:
            await session.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": ADVISORY_LOCK_KEY})
            await session.commit()
