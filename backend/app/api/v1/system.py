from fastapi import APIRouter

from app.services.polling_scheduler import scheduler

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/polling-status")
async def polling_status() -> dict:
    return scheduler.get_status()


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
