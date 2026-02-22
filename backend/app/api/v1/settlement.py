from __future__ import annotations

from fastapi import APIRouter

from app.tasks.settle import run_settlement_pipeline

router = APIRouter(prefix="/settlement", tags=["settlement"])


@router.post("/run")
async def run_settlement() -> dict:
    return await run_settlement_pipeline()
