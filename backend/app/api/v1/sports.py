from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends

from app.database import get_session
from app.models.sport import Sport

router = APIRouter(prefix="/sports", tags=["sports"])


@router.get("")
async def list_sports(session: AsyncSession = Depends(get_session)) -> list[dict]:
    sports = (await session.scalars(select(Sport))).all()
    return [{"key": s.key, "name": s.name, "active": s.active} for s in sports]
