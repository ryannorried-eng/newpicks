from fastapi import APIRouter

from app.api.v1.bankroll import router as bankroll_router
from app.api.v1.model import router as model_router
from app.api.v1.odds import router as odds_router
from app.api.v1.picks import router as picks_router
from app.api.v1.parlays import router as parlays_router
from app.api.v1.performance import router as performance_router
from app.api.v1.settlement import router as settlement_router
from app.api.v1.sports import router as sports_router
from app.api.v1.system import router as system_router

api_router = APIRouter()
api_router.include_router(sports_router)
api_router.include_router(odds_router)
api_router.include_router(picks_router)
api_router.include_router(parlays_router)
api_router.include_router(system_router)
api_router.include_router(performance_router)
api_router.include_router(bankroll_router)
api_router.include_router(settlement_router)

api_router.include_router(model_router)
