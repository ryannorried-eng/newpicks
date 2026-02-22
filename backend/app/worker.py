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

client = OddsAPIClient()


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


async def main() -> None:
    await startup_sync()
    await check_daily_schedule()
    await run_fetch_odds()

    sched = AsyncIOScheduler(timezone="UTC")
    sched.add_job(check_daily_schedule, "interval", hours=1)
    sched.add_job(run_fetch_odds, "interval", minutes=10)
    sched.start()

    while True:
        await asyncio.sleep(3600)


if __name__ == "__main__":
    asyncio.run(main())
