from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends

from app.database import get_session
from app.models.odds_snapshot import OddsSnapshot
from app.services.polling_scheduler import scheduler

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/polling-status")
async def polling_status() -> dict:
    return scheduler.get_status()


@router.get("/health")
async def health(session: AsyncSession = Depends(get_session)) -> dict[str, str | int | None]:
    snapshot_count_stmt = select(func.count(OddsSnapshot.id))
    last_snapshot_stmt = select(func.max(OddsSnapshot.snapshot_time))

    snapshot_count = int((await session.scalar(snapshot_count_stmt)) or 0)
    last_snapshot_time = await session.scalar(last_snapshot_stmt)

    return {
        "status": "ok",
        "snapshot_count": snapshot_count,
        "last_snapshot_time": last_snapshot_time.isoformat() if last_snapshot_time else None,
    }
