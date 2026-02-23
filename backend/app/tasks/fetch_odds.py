from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.data_providers.odds_api import OddsAPIClient
from app.models.game import Game
from app.models.odds_snapshot import OddsSnapshot
from app.models.sport import Sport
from app.services.polling_scheduler import scheduler
from app.utils.odds_math import american_to_implied_prob, remove_vig


logger = logging.getLogger(__name__)

SUPPORTED_GAME_SPORTS = {
    "basketball_nba",
    "americanfootball_nfl",
    "baseball_mlb",
    "icehockey_nhl",
    "basketball_wnba",
    "americanfootball_ncaaf",
    "basketball_ncaab",
}


async def sync_sports(client: OddsAPIClient, session: AsyncSession) -> None:
    sports = await client.get_sports()
    scheduler.update_quota(sports.requests_remaining)
    for item in sports.data:
        key = item.get("key")
        if not key:
            continue
        is_active = key in SUPPORTED_GAME_SPORTS and item.get("active", True)
        existing = await session.scalar(select(Sport).where(Sport.key == key))
        if existing is None:
            session.add(Sport(key=key, name=item.get("title", key), active=is_active))
            continue
        existing.name = item.get("title", key)
        existing.active = is_active

    unsupported_stmt = select(Sport).where(Sport.key.not_in(SUPPORTED_GAME_SPORTS), Sport.active.is_(True))
    unsupported_sports = await session.scalars(unsupported_stmt)
    for sport in unsupported_sports:
        sport.active = False
    await session.commit()


async def fetch_odds_adaptive(client: OddsAPIClient, session: AsyncSession) -> tuple[int, int]:
    sports: list[Sport] = list((await session.scalars(select(Sport).where(Sport.active.is_(True)))).all())
    total_games = 0
    total_snapshots = 0
    for sport in sports:
        if sport.key not in SUPPORTED_GAME_SPORTS:
            continue
        try:
            result = await client.get_odds(sport=sport.key, bookmakers=scheduler.poll_bookmakers())
        except Exception:
            logger.exception("Failed to fetch odds for sport %s", sport.key)
            continue
        scheduler.update_quota(result.requests_remaining)
        total_games += len(result.data)
        total_snapshots += await _store_odds_payload(session, sport.id, sport.key, result.data)
    return total_games, total_snapshots


async def _store_odds_payload(session: AsyncSession, sport_id: int, sport_key: str, payload: list[dict]) -> int:
    now = datetime.now(UTC)
    inserted = 0
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
                outcomes = market.get("outcomes", [])
                implied_probs = [american_to_implied_prob(int(outcome.get("price", 0))) if outcome.get("price") else 0.0 for outcome in outcomes]
                total_implied = sum(implied_probs)
                no_vig_probs = remove_vig(implied_probs) if total_implied > 0 else implied_probs

                for outcome, implied, no_vig in zip(outcomes, implied_probs, no_vig_probs):
                    side = outcome.get("name", "unknown").lower()
                    odds = int(outcome.get("price", 0))
                    line = outcome.get("point")
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
                        no_vig_prob=no_vig,
                        commence_time=commence,
                        snapshot_time=now,
                        snapshot_time_rounded=now.replace(second=0, microsecond=0),
                        is_closing=now >= (commence.replace(tzinfo=UTC) if commence.tzinfo is None else commence),
                    )
                    session.add(snapshot)
                    inserted += 1
    await session.commit()
    return inserted
