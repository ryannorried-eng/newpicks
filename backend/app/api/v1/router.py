from fastapi import APIRouter

from app.api.v1.odds import router as odds_router
from app.api.v1.picks import router as picks_router
from app.api.v1.sports import router as sports_router
from app.api.v1.system import router as system_router

api_router = APIRouter()
api_router.include_router(sports_router)
api_router.include_router(odds_router)
api_router.include_router(picks_router)
api_router.include_router(system_router)
