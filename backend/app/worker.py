import asyncio
import logging
from datetime import UTC, datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select, text

from app.config import settings
from app.data_providers.nba_stats import NBAStatsClient
from app.data_providers.odds_api import OddsAPIClient
from app.database import AsyncSessionLocal
from app.models.game import Game
from app.models.sport import Sport
from app.services.polling_scheduler import scheduler
from app.tasks.capture_closing_lines import capture_closing_lines
from app.tasks.fetch_odds import fetch_odds_adaptive, sync_sports
from app.tasks.generate_parlays import run_generate_parlays
from app.tasks.generate_picks import run_generate_picks
from app.tasks.settle import run_settlement_pipeline
from app.tasks.train_model import run_model_training

logger = logging.getLogger(__name__)

client = OddsAPIClient()
nba_client = NBAStatsClient()
_missing_odds_key_logged = False


async def check_daily_schedule() -> None:
    async with AsyncSessionLocal() as session:
        sports = (await session.scalars(select(Sport))).all()
        schedule: dict[str, list[datetime]] = {}
        for sport in sports:
            starts = (
                await session.scalars(
                    select(Game.commence_time).where(Game.sport_id == sport.id, Game.commence_time >= datetime.now(UTC))
                )
            ).all()
            schedule[sport.key] = list(starts)
        scheduler.check_daily_schedule(schedule)


async def startup_sync() -> None:
    async with AsyncSessionLocal() as session:
        await sync_sports(client, session)


async def run_fetch_odds() -> None:
    global _missing_odds_key_logged

    sleep_seconds = 600
    if not settings.odds_api_key:
        if not _missing_odds_key_logged:
            logger.error("ODDS_API_KEY is missing; skipping ingestion cycle until it is configured")
            _missing_odds_key_logged = True
        logger.info("odds polling cycle skipped: games=0 snapshots_inserted=0 next_sleep_seconds=%s", sleep_seconds)
        return

    _missing_odds_key_logged = False
    try:
        async with AsyncSessionLocal() as session:
            games_fetched, snapshots_inserted = await fetch_odds_adaptive(client, session)
    except Exception:
        sleep_seconds = 60
        logger.exception("odds polling cycle failed; applying backoff")
        logger.info("odds polling cycle failed: games=0 snapshots_inserted=0 next_sleep_seconds=%s", sleep_seconds)
        await asyncio.sleep(sleep_seconds)
        return

    logger.info(
        "odds polling cycle complete: games=%s snapshots_inserted=%s next_sleep_seconds=%s",
        games_fetched,
        snapshots_inserted,
        sleep_seconds,
    )


async def run_model_training_task() -> None:
    await run_model_training(nba_client)


async def run_generate_picks_task() -> None:
    await run_generate_picks()


async def run_generate_parlays_task() -> None:
    await run_generate_parlays()


async def run_capture_closing_lines_task() -> None:
    async with AsyncSessionLocal() as session:
        lock = await session.scalar(text("SELECT pg_try_advisory_lock(:key)"), {"key": 927413})
        if not lock:
            return
        try:
            await capture_closing_lines(session)
        finally:
            await session.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": 927413})
            await session.commit()


async def run_settlement_pipeline_task() -> None:
    await run_settlement_pipeline()


async def main() -> None:
    await startup_sync()
    await check_daily_schedule()
    try:
        await run_fetch_odds()
    except Exception:
        pass

    sched = AsyncIOScheduler(timezone="UTC")
    sched.add_job(check_daily_schedule, "interval", hours=1)
    sched.add_job(run_fetch_odds, "interval", minutes=10)
    sched.add_job(run_capture_closing_lines_task, "interval", minutes=10)
    sched.add_job(run_settlement_pipeline_task, "interval", minutes=30)
    sched.add_job(run_model_training_task, "cron", day_of_week="sun", hour=8, minute=0)
    sched.add_job(run_generate_picks_task, "cron", hour=13, minute=0)
    sched.add_job(run_generate_parlays_task, "cron", hour=13, minute=15)
    sched.start()

    while True:
        await asyncio.sleep(3600)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")
    asyncio.run(main())
