from __future__ import annotations

from sqlalchemy import text

from app.data_providers.odds_api import OddsAPIClient
from app.database import AsyncSessionLocal
from app.services.clv_service import calculate_all_pending_clv
from app.services.parlay_settlement import settle_parlays
from app.services.settlement_service import settle_picks
from app.tasks.capture_closing_lines import capture_closing_lines
from app.tasks.fetch_results import fetch_game_results

ADVISORY_LOCK_KEY = 927412


async def run_settlement_pipeline() -> dict:
    client = OddsAPIClient()
    async with AsyncSessionLocal() as session:
        lock = await session.scalar(text("SELECT pg_try_advisory_lock(:key)"), {"key": ADVISORY_LOCK_KEY})
        if not lock:
            return {
                "games_updated": 0,
                "closing_lines_marked": 0,
                "picks_settled": 0,
                "clv_calculated": 0,
                "parlays_settled": 0,
            }
        try:
            games_updated = await fetch_game_results(client, session)
            closing_marked = await capture_closing_lines(session)
            picks_result = await settle_picks(session)
            clv_updated = await calculate_all_pending_clv(session)
            parlay_result = await settle_parlays(session)
            return {
                "games_updated": games_updated,
                "closing_lines_marked": closing_marked,
                "picks_settled": picks_result["settled"],
                "clv_calculated": clv_updated,
                "parlays_settled": parlay_result["settled"],
            }
        finally:
            await session.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": ADVISORY_LOCK_KEY})
            await session.commit()
