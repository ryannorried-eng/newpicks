from __future__ import annotations

from sqlalchemy import text

from app.database import AsyncSessionLocal
from app.services.pick_service import generate_picks

ADVISORY_LOCK_KEY = 927410


async def run_generate_picks() -> dict[str, int | str]:
    async with AsyncSessionLocal() as session:
        lock = await session.scalar(text("SELECT pg_try_advisory_lock(:key)"), {"key": ADVISORY_LOCK_KEY})
        if not lock:
            return {"picks_created": 0, "picks_updated": 0, "generated_at": "", "lock_acquired": 0}
        try:
            summary = await generate_picks(session)
            summary["lock_acquired"] = 1
            return summary
        finally:
            await session.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": ADVISORY_LOCK_KEY})
            await session.commit()
