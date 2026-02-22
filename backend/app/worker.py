import asyncio
from datetime import UTC, datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from app.data_providers.odds_api import OddsAPIClient
from app.database import AsyncSessionLocal
from app.models.game import Game
from app.models.sport import Sport
from app.services.polling_scheduler import scheduler
from app.tasks.fetch_odds import fetch_odds_adaptive, sync_sports
from app.tasks.generate_picks import run_generate_picks
from app.tasks.generate_parlays import run_generate_parlays
from app.tasks.settle import run_settlement_pipeline
from app.tasks.capture_closing_lines import capture_closing_lines
from app.tasks.train_model import run_model_training
from app.data_providers.nba_stats import NBAStatsClient
from sqlalchemy import text

client = OddsAPIClient()
nba_client = NBAStatsClient()


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
    async with AsyncSessionLocal() as session:
        await fetch_odds_adaptive(client, session)



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
    await run_fetch_odds()

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
    asyncio.run(main())
