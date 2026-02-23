from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import and_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.game import Game
from app.models.odds_snapshot import OddsSnapshot
from app.models.pick import Pick
from app.services.model_provider import model_provider
from app.utils.odds_math import american_to_decimal, american_to_implied_prob, calculate_ev

logger = logging.getLogger(__name__)
MARKETS = ("h2h", "spreads", "totals")
DEFAULT_TOP_N = 3
DEFAULT_LOOKBACK_MINUTES = 60
DEFAULT_MIN_EV_THRESHOLD = 0.015


@dataclass(slots=True)
class PickCandidate:
    game: Game
    sport_key: str
    market: str
    side: str
    line: float | None
    best_book: str
    best_odds: int
    snapshot_time_open: datetime
    implied_prob_open: float
    consensus_prob: float
    book_count: int
    model_prob: float
    edge: float
    ev_pct: float


def _probability_for_snapshot(snapshot: OddsSnapshot) -> float:
    if snapshot.no_vig_prob is not None and snapshot.no_vig_prob > 0:
        return snapshot.no_vig_prob
    return american_to_implied_prob(snapshot.odds)


async def generate_picks(
    session: AsyncSession,
    *,
    lookback_minutes: int = DEFAULT_LOOKBACK_MINUTES,
    top_n_per_sport_market: int = DEFAULT_TOP_N,
    min_ev_threshold: float = DEFAULT_MIN_EV_THRESHOLD,
) -> dict[str, int | str]:
    now = datetime.now(UTC)
    since = now - timedelta(minutes=lookback_minutes)
    pick_day = now.date()
    pick_date = now.replace(hour=0, minute=0, second=0, microsecond=0)

    rows = (
        await session.scalars(
            select(OddsSnapshot)
            .where(and_(OddsSnapshot.snapshot_time >= since, OddsSnapshot.market.in_(MARKETS)))
            .order_by(
                OddsSnapshot.game_id,
                OddsSnapshot.market,
                OddsSnapshot.side,
                OddsSnapshot.bookmaker,
                OddsSnapshot.snapshot_time.desc(),
            )
        )
    ).all()
    if not rows:
        return {
            "picks_created": 0,
            "picks_updated": 0,
            "picks_skipped_no_model": 0,
            "generated_at": now.isoformat(),
        }

    latest_by_book: dict[tuple[int, str, str, str], OddsSnapshot] = {}
    for row in rows:
        key = (row.game_id, row.market, row.side, row.bookmaker)
        if key not in latest_by_book:
            latest_by_book[key] = row

    grouped_by_side: dict[tuple[int, str, str], list[OddsSnapshot]] = defaultdict(list)
    for row in latest_by_book.values():
        grouped_by_side[(row.game_id, row.market, row.side)].append(row)

    game_ids = {k[0] for k in grouped_by_side.keys()}
    game_map = {g.id: g for g in (await session.scalars(select(Game).where(Game.id.in_(game_ids)))).all()}

    candidates: list[PickCandidate] = []
    skipped_no_model = 0
    for (game_id, market, side), side_rows in grouped_by_side.items():
        game = game_map.get(game_id)
        if game is None:
            continue

        consensus_probs = [_probability_for_snapshot(r) for r in side_rows]
        consensus_prob = sum(consensus_probs) / len(consensus_probs)
        best_row = max(side_rows, key=lambda r: american_to_decimal(r.odds))
        implied_prob_open = american_to_implied_prob(best_row.odds)

        model_prob = await model_provider.get_true_prob(
            sport_key=best_row.sport_key,
            game=game,
            market=market,
            side=side,
            line=best_row.line,
            context={"consensus_prob": consensus_prob},
        )
        if model_prob is None:
            skipped_no_model += 1
            continue

        edge = model_prob - implied_prob_open
        ev_pct = calculate_ev(model_prob, american_to_decimal(best_row.odds))
        if ev_pct < min_ev_threshold:
            continue

        candidates.append(
            PickCandidate(
                game=game,
                sport_key=best_row.sport_key,
                market=market,
                side=side,
                line=best_row.line,
                best_book=best_row.bookmaker,
                best_odds=best_row.odds,
                snapshot_time_open=best_row.snapshot_time,
                implied_prob_open=implied_prob_open,
                consensus_prob=consensus_prob,
                book_count=len(side_rows),
                model_prob=model_prob,
                edge=edge,
                ev_pct=ev_pct,
            )
        )

    selected: list[PickCandidate] = []
    by_sport_market: dict[tuple[str, str], list[PickCandidate]] = defaultdict(list)
    for c in candidates:
        by_sport_market[(c.sport_key, c.market)].append(c)
    for _, bucket in by_sport_market.items():
        selected.extend(sorted(bucket, key=lambda c: c.edge, reverse=True)[:top_n_per_sport_market])

    existing_keys = {
        (p.game_id, p.market, p.side)
        for p in (
            await session.scalars(select(Pick).where(Pick.pick_day == pick_day))
        ).all()
    }

    created = 0
    updated = 0
    for c in selected:
        dialect = session.bind.dialect.name if session.bind is not None else "postgresql"
        insert_stmt = (sqlite_insert(Pick) if dialect == "sqlite" else pg_insert(Pick)).values(
            game_id=c.game.id,
            sport_key=c.sport_key,
            pick_date=pick_date,
            pick_day=pick_day,
            market=c.market,
            side=c.side,
            line=c.line,
            odds_american=c.best_odds,
            best_book=c.best_book,
            issued_at=now,
            snapshot_time_open=c.snapshot_time_open,
            model_prob=c.model_prob,
            implied_prob_open=c.implied_prob_open,
            ev_pct=c.ev_pct,
            edge=c.edge,
            consensus_prob=c.consensus_prob,
            book_count=c.book_count,
            fair_prob=c.model_prob,
            prob_source="model_provider",
            implied_prob=c.implied_prob_open,
            composite_score=c.edge * 100,
            confidence_tier="high" if c.ev_pct >= 0.03 else "medium",
            signals={"model_driven": True},
            data_quality={"lookback_minutes": lookback_minutes},
            suggested_kelly_fraction=0.0,
            status="open",
        )
        if dialect == "sqlite":
            on_conflict = insert_stmt.on_conflict_do_update(
                index_elements=["game_id", "market", "side", "pick_day"],
                set_={
                    "model_prob": c.model_prob,
                    "ev_pct": c.ev_pct,
                    "edge": c.edge,
                    "consensus_prob": c.consensus_prob,
                    "book_count": c.book_count,
                    "fair_prob": c.model_prob,
                    "implied_prob": c.implied_prob_open,
                    "composite_score": c.edge * 100,
                    "signals": {"model_driven": True, "updated": True},
                    "data_quality": {"lookback_minutes": lookback_minutes},
                },
            )
        else:
            on_conflict = insert_stmt.on_conflict_do_update(
                constraint="uq_pick_game_market_side_day",
                set_={
                "model_prob": c.model_prob,
                "ev_pct": c.ev_pct,
                "edge": c.edge,
                "consensus_prob": c.consensus_prob,
                "book_count": c.book_count,
                "fair_prob": c.model_prob,
                "implied_prob": c.implied_prob_open,
                "composite_score": c.edge * 100,
                "signals": {"model_driven": True, "updated": True},
                "data_quality": {"lookback_minutes": lookback_minutes},
            },
            )
        )

        await session.execute(on_conflict)
        key = (c.game.id, c.market, c.side)
        if key in existing_keys:
            updated += 1
        else:
            created += 1
            existing_keys.add(key)

    await session.commit()

    return {
        "picks_created": created,
        "picks_updated": updated,
        "picks_skipped_no_model": skipped_no_model,
        "generated_at": now.isoformat(),
    }


async def update_closing_lines_for_open_picks(session: AsyncSession, *, pregame_grace_minutes: int = 5) -> int:
    now = datetime.now(UTC)
    cutoff = now + timedelta(minutes=pregame_grace_minutes)

    open_picks = (
        await session.scalars(
            select(Pick)
            .join(Game, Game.id == Pick.game_id)
            .where(Pick.status == "open", Game.commence_time <= cutoff, Pick.closing_snapshot_time.is_(None))
        )
    ).all()

    updated = 0
    for pick in open_picks:
        # pick is Pick due scalars over first col in join
        game = await session.scalar(select(Game).where(Game.id == pick.game_id))
        if game is None:
            continue

        closing = await session.scalar(
            select(OddsSnapshot)
            .where(
                OddsSnapshot.game_id == pick.game_id,
                OddsSnapshot.market == pick.market,
                OddsSnapshot.side == pick.side,
                OddsSnapshot.bookmaker == pick.best_book,
                OddsSnapshot.snapshot_time <= game.commence_time,
            )
            .order_by(OddsSnapshot.snapshot_time.desc())
            .limit(1)
        )
        if closing is None:
            closing = await session.scalar(
                select(OddsSnapshot)
                .where(
                    OddsSnapshot.game_id == pick.game_id,
                    OddsSnapshot.market == pick.market,
                    OddsSnapshot.side == pick.side,
                    OddsSnapshot.snapshot_time <= game.commence_time,
                )
                .order_by(OddsSnapshot.snapshot_time.desc())
                .limit(1)
            )
        if closing is None:
            continue

        clv_prob = american_to_implied_prob(closing.odds) - (pick.implied_prob_open or american_to_implied_prob(pick.odds_american))
        open_dec = american_to_decimal(pick.odds_american)
        close_dec = american_to_decimal(closing.odds)

        pick.closing_odds_american = closing.odds
        pick.closing_line = closing.line
        pick.closing_snapshot_time = closing.snapshot_time
        pick.clv_prob = clv_prob
        pick.clv_price = open_dec - close_dec
        updated += 1

    if updated:
        await session.commit()
    return updated
