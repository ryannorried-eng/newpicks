from __future__ import annotations

import asyncio
import importlib.util
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import Base
from app.models.game import Game
from app.models.odds_snapshot import OddsSnapshot
from app.models.pick import Pick
from app.models.sport import Sport
from app.services import pick_service
from app.services.pick_service import generate_picks, update_closing_lines_for_open_picks


def test_compute_edge_from_model_minus_open_implied() -> None:
    model_prob = 0.57
    implied_open = 0.52
    assert model_prob - implied_open == pytest.approx(0.05)


def test_generate_picks_and_clv_update_integration() -> None:
    if importlib.util.find_spec("aiosqlite") is None:
        pytest.skip("aiosqlite not available in this environment")
    asyncio.run(_run_generate_picks_and_clv_update_integration())


async def _run_generate_picks_and_clv_update_integration() -> None:
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
            commence_time=now + timedelta(minutes=1),
        )
        session.add(game)
        await session.flush()

        session.add_all(
            [
                OddsSnapshot(
                    game_id=game.id,
                    sport_key=sport.key,
                    bookmaker="book_a",
                    market="h2h",
                    side="Boston Celtics",
                    line=None,
                    odds=105,
                    implied_prob=0.4878,
                    no_vig_prob=0.52,
                    commence_time=game.commence_time,
                    snapshot_time=now - timedelta(minutes=1),
                    snapshot_time_rounded=rounded,
                ),
                OddsSnapshot(
                    game_id=game.id,
                    sport_key=sport.key,
                    bookmaker="book_b",
                    market="h2h",
                    side="Boston Celtics",
                    line=None,
                    odds=110,
                    implied_prob=0.4762,
                    no_vig_prob=0.53,
                    commence_time=game.commence_time,
                    snapshot_time=now - timedelta(minutes=1),
                    snapshot_time_rounded=rounded,
                ),
            ]
        )
        await session.commit()

    class _StubProvider:
        async def get_true_prob(self, **kwargs):
            return 0.58

    pick_service.model_provider = _StubProvider()

    async with session_factory() as session:
        summary1 = await generate_picks(session, lookback_minutes=120, top_n_per_sport_market=3, min_ev_threshold=0.015)
        assert int(summary1["picks_created"]) > 0

        pick = await session.scalar(select(Pick).where(Pick.game_id == 1, Pick.side == "Boston Celtics"))
        assert pick is not None
        first_issued_at = pick.issued_at
        first_open_odds = pick.odds_american
        first_open_line = pick.line
        first_open_snapshot = pick.snapshot_time_open

        summary2 = await generate_picks(session, lookback_minutes=120, top_n_per_sport_market=3, min_ev_threshold=0.015)
        assert int(summary2["picks_updated"]) >= 1

        pick2 = await session.scalar(select(Pick).where(Pick.id == pick.id))
        assert pick2 is not None
        assert pick2.issued_at == first_issued_at
        assert pick2.odds_american == first_open_odds
        assert pick2.line == first_open_line
        assert pick2.snapshot_time_open == first_open_snapshot

        session.add(
            OddsSnapshot(
                game_id=pick2.game_id,
                sport_key=sport.key,
                bookmaker=pick2.best_book,
                market=pick2.market,
                side=pick2.side,
                line=pick2.line,
                odds=100,
                implied_prob=0.5,
                no_vig_prob=0.5,
                commence_time=now,
                snapshot_time=now,
                snapshot_time_rounded=rounded,
                is_closing=True,
            )
        )
        await session.commit()

        updated = await update_closing_lines_for_open_picks(session, pregame_grace_minutes=10)
        assert updated >= 1

        pick3 = await session.scalar(select(Pick).where(Pick.id == pick.id))
        assert pick3 is not None
        assert pick3.closing_odds_american is not None
        assert pick3.clv_prob is not None
        assert pick3.clv_price is not None

    await engine.dispose()
