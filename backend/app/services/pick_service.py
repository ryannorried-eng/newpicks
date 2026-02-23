from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import and_, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.game import Game
from app.models.odds_snapshot import OddsSnapshot
from app.models.pick import Pick
from app.models.sport import Sport
from app.utils.odds_math import american_to_decimal, american_to_implied_prob, kelly_criterion

logger = logging.getLogger(__name__)
MARKETS = ("h2h", "spreads", "totals")
DEFAULT_TOP_N = 3
DEFAULT_LOOKBACK_MINUTES = 60


@dataclass(slots=True)
class PickCandidate:
    game_id: int
    sport_key: str
    market: str
    side: str
    line: float | None
    best_book: str
    best_odds: int
    best_implied_prob: float
    consensus_prob: float
    edge: float


def _probability_for_snapshot(snapshot: OddsSnapshot) -> float:
    no_vig = getattr(snapshot, "no_vig_prob", None)
    if no_vig is not None and no_vig > 0:
        return no_vig
    return american_to_implied_prob(snapshot.odds)


def compute_edge(consensus_prob: float, best_price_implied_prob: float) -> float:
    return consensus_prob - best_price_implied_prob


async def generate_picks(
    session: AsyncSession,
    *,
    lookback_minutes: int = DEFAULT_LOOKBACK_MINUTES,
    top_n_per_sport_market: int = DEFAULT_TOP_N,
) -> dict[str, int | str]:
    now = datetime.now(UTC)
    since = now - timedelta(minutes=lookback_minutes)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    latest_snapshot_time = await session.scalar(
        select(func.max(OddsSnapshot.snapshot_time)).where(OddsSnapshot.snapshot_time >= since)
    )
    if latest_snapshot_time is None:
        logger.info("pick generation skipped: no odds snapshots in lookback window")
        return {"picks_created": 0, "picks_updated": 0, "generated_at": now.isoformat()}

    latest_rows = (
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

    latest_by_book: dict[tuple[int, str, str, str], OddsSnapshot] = {}
    for row in latest_rows:
        key = (row.game_id, row.market, row.side, row.bookmaker)
        if key not in latest_by_book:
            latest_by_book[key] = row

    grouped_by_side: dict[tuple[int, str, str], list[OddsSnapshot]] = defaultdict(list)
    for row in latest_by_book.values():
        grouped_by_side[(row.game_id, row.market, row.side)].append(row)

    candidates: list[PickCandidate] = []
    for (game_id, market, side), rows in grouped_by_side.items():
        if not rows:
            continue

        probs = [_probability_for_snapshot(row) for row in rows]
        consensus_prob = sum(probs) / len(probs)

        best_row = max(rows, key=lambda row: american_to_decimal(row.odds))
        best_implied_prob = american_to_implied_prob(best_row.odds)
        edge = compute_edge(consensus_prob, best_implied_prob)
        if edge <= 0:
            continue

        candidates.append(
            PickCandidate(
                game_id=game_id,
                sport_key=best_row.sport_key,
                market=market,
                side=side,
                line=best_row.line,
                best_book=best_row.bookmaker,
                best_odds=best_row.odds,
                best_implied_prob=best_implied_prob,
                consensus_prob=consensus_prob,
                edge=edge,
            )
        )

    if not candidates:
        await session.execute(delete(Pick).where(Pick.pick_date >= today_start))
        await session.commit()
        logger.info("pick generation complete: picks_created=0 picks_updated=0")
        return {"picks_created": 0, "picks_updated": 0, "generated_at": now.isoformat()}

    game_map = {
        game.id: game
        for game in (
            await session.scalars(select(Game).where(Game.id.in_({candidate.game_id for candidate in candidates})))
        ).all()
    }
    sport_map = {
        sport.id: sport.key
        for sport in (
            await session.scalars(select(Sport)).all()
        )
    }

    selected: list[PickCandidate] = []
    by_sport_market: dict[tuple[str, str], list[PickCandidate]] = defaultdict(list)
    for candidate in candidates:
        by_sport_market[(candidate.sport_key, candidate.market)].append(candidate)

    for key, bucket in by_sport_market.items():
        ranked = sorted(bucket, key=lambda item: item.edge, reverse=True)
        selected.extend(ranked[:top_n_per_sport_market])
        logger.info(
            "pick generation bucket: sport=%s market=%s selected=%s available=%s",
            key[0],
            key[1],
            min(top_n_per_sport_market, len(ranked)),
            len(ranked),
        )

    await session.execute(delete(Pick).where(Pick.pick_date >= today_start))

    picks_to_insert: list[Pick] = []
    for candidate in selected:
        game = game_map.get(candidate.game_id)
        sport_key = candidate.sport_key
        if game is not None:
            sport_key = sport_map.get(game.sport_id, sport_key)

        dec_odds = american_to_decimal(candidate.best_odds)
        kelly = kelly_criterion(candidate.consensus_prob, dec_odds)
        picks_to_insert.append(
            Pick(
                game_id=candidate.game_id,
                sport_key=sport_key,
                pick_date=today_start,
                market=candidate.market,
                side=candidate.side,
                line=candidate.line,
                odds_american=candidate.best_odds,
                best_book=candidate.best_book,
                fair_prob=candidate.consensus_prob,
                prob_source="consensus",
                implied_prob=candidate.best_implied_prob,
                ev_pct=candidate.edge,
                composite_score=candidate.edge * 100,
                confidence_tier="medium" if candidate.edge < 0.03 else "high",
                signals={"edge": candidate.edge, "books_in_consensus": len(grouped_by_side[(candidate.game_id, candidate.market, candidate.side)])},
                data_quality={"latest_snapshot_time": latest_snapshot_time.isoformat(), "lookback_minutes": lookback_minutes},
                suggested_kelly_fraction=kelly,
            )
        )

    session.add_all(picks_to_insert)
    await session.commit()

    picks_created = len(picks_to_insert)
    logger.info("pick generation complete: picks_created=%s picks_updated=0", picks_created)
    return {"picks_created": picks_created, "picks_updated": 0, "generated_at": now.isoformat()}


async def generate_daily_picks(session: AsyncSession) -> list[Pick]:
    summary = await generate_picks(session)
    if summary["picks_created"] == 0:
        return []
    now = datetime.now(UTC)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return (
        await session.scalars(select(Pick).where(Pick.pick_date >= today_start).order_by(Pick.ev_pct.desc()))
    ).all()
