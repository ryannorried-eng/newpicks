from __future__ import annotations

from datetime import UTC, datetime, timedelta
import asyncio
import importlib.util

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import Base
from app.models.game import Game
from app.models.odds_snapshot import OddsSnapshot
from app.models.pick import Pick
from app.models.sport import Sport
from app.services.pick_service import compute_edge, generate_picks


@pytest.mark.parametrize(
    ("consensus_prob", "best_implied_prob", "expected"),
    [
        (0.56, 0.50, 0.06),
        (0.50, 0.52, -0.02),
        (0.525, 0.525, 0.0),
    ],
)
def test_compute_edge(consensus_prob: float, best_implied_prob: float, expected: float) -> None:
    assert compute_edge(consensus_prob, best_implied_prob) == pytest.approx(expected)


def test_generate_picks_creates_rows_from_synthetic_odds() -> None:
    if importlib.util.find_spec("aiosqlite") is None:
        pytest.skip("aiosqlite not available in this environment")
    asyncio.run(_run_generate_picks_creates_rows_from_synthetic_odds())


async def _run_generate_picks_creates_rows_from_synthetic_odds() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    now = datetime.now(UTC)
    rounded = now.replace(second=0, microsecond=0)

    async with session_factory() as session:
        sport = Sport(key="basketball_nba", name="NBA", active=True)
        session.add(sport)
        await session.flush()

        game = Game(
            external_id="game-1",
            sport_id=sport.id,
            home_team="Boston Celtics",
            away_team="Miami Heat",
            commence_time=now + timedelta(hours=2),
        )
        session.add(game)
        await session.flush()

        rows = [
            OddsSnapshot(
                game_id=game.id,
                sport_key="basketball_nba",
                bookmaker="book_a",
                market="h2h",
                side="Boston Celtics",
                line=None,
                odds=110,
                implied_prob=0.476,
                no_vig_prob=0.52,
                commence_time=game.commence_time,
                snapshot_time=now,
                snapshot_time_rounded=rounded,
            ),
            OddsSnapshot(
                game_id=game.id,
                sport_key="basketball_nba",
                bookmaker="book_b",
                market="h2h",
                side="Boston Celtics",
                line=None,
                odds=105,
                implied_prob=0.488,
                no_vig_prob=0.54,
                commence_time=game.commence_time,
                snapshot_time=now,
                snapshot_time_rounded=rounded,
            ),
            OddsSnapshot(
                game_id=game.id,
                sport_key="basketball_nba",
                bookmaker="book_a",
                market="h2h",
                side="Miami Heat",
                line=None,
                odds=-120,
                implied_prob=0.545,
                no_vig_prob=0.48,
                commence_time=game.commence_time,
                snapshot_time=now,
                snapshot_time_rounded=rounded,
            ),
            OddsSnapshot(
                game_id=game.id,
                sport_key="basketball_nba",
                bookmaker="book_b",
                market="h2h",
                side="Miami Heat",
                line=None,
                odds=-125,
                implied_prob=0.556,
                no_vig_prob=0.46,
                commence_time=game.commence_time,
                snapshot_time=now,
                snapshot_time_rounded=rounded,
            ),
        ]
        session.add_all(rows)
        await session.commit()

    async with session_factory() as session:
        summary = await generate_picks(session, lookback_minutes=120, top_n_per_sport_market=3)
        assert int(summary["picks_created"]) > 0

        picks = (await session.scalars(select(Pick))).all()
        assert len(picks) > 0

    await engine.dispose()
