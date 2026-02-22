from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.data_providers.odds_api import OddsAPIClient
from app.models.game import Game
from app.models.sport import Sport

logger = logging.getLogger(__name__)


async def fetch_game_results(client: OddsAPIClient, session: AsyncSession) -> int:
    cutoff = datetime.now(UTC) - timedelta(hours=3)
    stale_games = (
        await session.scalars(select(Game).where(and_(Game.commence_time < cutoff, Game.result_fetched.is_(False))))
    ).all()
    if not stale_games:
        return 0

    sport_ids = {g.sport_id for g in stale_games}
    sports = (await session.scalars(select(Sport).where(Sport.id.in_(sport_ids)))).all()
    sport_by_id = {s.id: s for s in sports}

    updated = 0
    for sport_id in sport_ids:
        sport = sport_by_id.get(sport_id)
        if sport is None:
            continue
        try:
            result = await client.get_scores(sport.key)
        except Exception:
            logger.exception("Failed to fetch scores for sport %s", sport.key)
            continue

        by_external = {g.external_id: g for g in stale_games if g.sport_id == sport_id}
        for row in result.data:
            if not row.get("completed"):
                continue
            game = by_external.get(row.get("id"))
            if game is None:
                continue

            scores = row.get("scores") or []
            name_to_score: dict[str, int] = {}
            for item in scores:
                name = (item.get("name") or "").strip().lower()
                score_raw = item.get("score")
                if not name or score_raw is None:
                    continue
                try:
                    name_to_score[name] = int(score_raw)
                except (TypeError, ValueError):
                    continue

            home_score = name_to_score.get(game.home_team.strip().lower())
            away_score = name_to_score.get(game.away_team.strip().lower())
            if home_score is None or away_score is None:
                continue

            game.home_score = home_score
            game.away_score = away_score
            game.completed = True
            game.result_fetched = True
            updated += 1

    await session.commit()
    return updated
