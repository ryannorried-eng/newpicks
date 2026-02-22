from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.data_providers.odds_api import OddsAPIClient
from app.models.game import Game
from app.models.odds_snapshot import OddsSnapshot
from app.models.sport import Sport
from app.services.polling_scheduler import scheduler
from app.utils.odds_math import american_to_implied_prob


async def sync_sports(client: OddsAPIClient, session: AsyncSession) -> None:
    sports = await client.get_sports()
    scheduler.update_quota(sports.requests_remaining)
    for item in sports.data:
        key = item.get("key")
        if not key:
            continue
        existing = await session.scalar(select(Sport).where(Sport.key == key))
        if existing is None:
            session.add(Sport(key=key, name=item.get("title", key), active=item.get("active", True)))
    await session.commit()


async def fetch_odds_adaptive(client: OddsAPIClient, session: AsyncSession) -> None:
    sports: list[Sport] = list((await session.scalars(select(Sport).where(Sport.active.is_(True)))).all())
    for sport in sports:
        result = await client.get_odds(sport=sport.key, bookmakers=scheduler.poll_bookmakers())
        scheduler.update_quota(result.requests_remaining)
        await _store_odds_payload(session, sport.id, sport.key, result.data)


async def _store_odds_payload(session: AsyncSession, sport_id: int, sport_key: str, payload: list[dict]) -> None:
    now = datetime.now(UTC)
    for game_data in payload:
        commence = datetime.fromisoformat(game_data["commence_time"].replace("Z", "+00:00"))
        game = await session.scalar(select(Game).where(Game.external_id == game_data["id"]))
        if game is None:
            game = Game(
                external_id=game_data["id"],
                sport_id=sport_id,
                home_team=game_data.get("home_team", "Home"),
                away_team=game_data.get("away_team", "Away"),
                commence_time=commence,
            )
            session.add(game)
            await session.flush()

        for bookmaker in game_data.get("bookmakers", []):
            for market in bookmaker.get("markets", []):
                for outcome in market.get("outcomes", []):
                    side = outcome.get("name", "unknown").lower()
                    odds = int(outcome.get("price", 0))
                    line = outcome.get("point")
                    implied = american_to_implied_prob(odds) if odds else 0.0
                    existing_stmt: Select[tuple[OddsSnapshot]] = (
                        select(OddsSnapshot)
                        .where(
                            OddsSnapshot.game_id == game.id,
                            OddsSnapshot.bookmaker == bookmaker["key"],
                            OddsSnapshot.market == market["key"],
                            OddsSnapshot.side == side,
                        )
                        .order_by(OddsSnapshot.snapshot_time.desc())
                        .limit(1)
                    )
                    prev = await session.scalar(existing_stmt)
                    if prev and prev.odds == odds and prev.line == line:
                        continue

                    snapshot = OddsSnapshot(
                        game_id=game.id,
                        sport_key=sport_key,
                        bookmaker=bookmaker["key"],
                        market=market["key"],
                        side=side,
                        line=line,
                        odds=odds,
                        implied_prob=implied,
                        no_vig_prob=implied,
                        commence_time=commence,
                        snapshot_time=now,
                        snapshot_time_rounded=now.replace(second=0, microsecond=0),
                        is_closing=now >= (commence.replace(tzinfo=UTC) if commence.tzinfo is None else commence),
                    )
                    session.add(snapshot)
    await session.commit()
