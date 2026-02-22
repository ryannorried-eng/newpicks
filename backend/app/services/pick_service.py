from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import and_, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.confidence import ConfidenceTier, assign_confidence
from app.analytics.consensus import calculate_consensus
from app.analytics.data_quality import assess_game_quality, data_quality_to_dict
from app.analytics.ev_calculator import calculate_pick_ev
from app.analytics.line_movement import (
    detect_reverse_line_movement,
    detect_steam_move,
    get_opening_to_current_change,
)
from app.analytics.sharp_signals import score_signals, signal_to_dict
from app.data_providers.nba_stats import NBAStatsClient
from app.ml.features import build_game_features, features_to_array
from app.ml.model import predictor
from app.models.game import Game
from app.models.odds_snapshot import OddsSnapshot
from app.models.pick import Pick
from app.utils.odds_math import american_to_decimal, kelly_criterion

logger = logging.getLogger(__name__)
MARKETS = ("h2h", "spreads", "totals")


async def generate_consensus_picks(session: AsyncSession, games: list[Game], today_start: datetime) -> list[Pick]:
    generated: list[Pick] = []
    for game in games:
        snapshots = (
            await session.scalars(
                select(OddsSnapshot).where(OddsSnapshot.game_id == game.id).order_by(OddsSnapshot.snapshot_time.asc())
            )
        ).all()
        if not snapshots:
            continue

        dq = assess_game_quality(game.id, snapshots)
        for market in MARKETS:
            consensus = calculate_consensus(snapshots, market)
            for side, side_data in consensus.items():
                ev = calculate_pick_ev(side_data["fair_prob"], side_data["best_odds"])
                steam = detect_steam_move(game.id, market, side, snapshots)
                rlm = detect_reverse_line_movement(game.id, market, side, snapshots)
                change = get_opening_to_current_change(game.id, market, side, snapshots)

                signals = score_signals(
                    ev_pct=ev["ev_pct"],
                    steam=steam,
                    rlm=rlm,
                    opening_odds=change["opening_odds"],
                    current_odds=change["current_odds"],
                    is_outlier_book=side_data["is_outlier"],
                    data_quality=dq,
                )

                signals_firing = int(signals.ev_positive + signals.steam_move + signals.reverse_line_movement + signals.best_line_available + signals.consensus_deviation)
                tier = assign_confidence(signals.composite, ev["ev_pct"], signals_firing, dq)
                if tier == ConfidenceTier.FILTERED:
                    continue

                dec_odds = american_to_decimal(side_data["best_odds"])
                kelly = kelly_criterion(ev["fair_prob"], dec_odds)
                latest_for_side = [s for s in snapshots if s.market == market and s.side == side]
                line = latest_for_side[-1].line if latest_for_side else None

                generated.append(
                    Pick(
                        game_id=game.id,
                        sport_key=snapshots[-1].sport_key,
                        pick_date=today_start,
                        market=market,
                        side=side,
                        line=line,
                        odds_american=side_data["best_odds"],
                        best_book=side_data["best_book"] or "unknown",
                        fair_prob=ev["fair_prob"],
                        prob_source="consensus",
                        implied_prob=ev["implied_prob_at_best_odds"],
                        ev_pct=ev["ev_pct"],
                        composite_score=signals.composite,
                        confidence_tier=tier.value,
                        signals=signal_to_dict(signals),
                        data_quality=data_quality_to_dict(dq),
                        suggested_kelly_fraction=kelly,
                    )
                )
    return generated


async def generate_model_picks(session: AsyncSession, games: list[Game], today_start: datetime) -> list[Pick]:
    if not predictor.is_trained:
        return []

    generated: list[Pick] = []
    nba_client = NBAStatsClient()
    seasons = {g.commence_time.date().year for g in games}
    for season in seasons:
        if not await nba_client.get_team_stats(season, use_cache=True):
            logger.info("Skipping model picks: missing cached team stats for season %s", season)
            return []

    for game in games:
        snapshots = (
            await session.scalars(
                select(OddsSnapshot).where(OddsSnapshot.game_id == game.id).order_by(OddsSnapshot.snapshot_time.asc())
            )
        ).all()
        if not snapshots:
            continue
        if snapshots[-1].sport_key != "basketball_nba":
            continue

        dq = assess_game_quality(game.id, snapshots)
        consensus = calculate_consensus(snapshots, "h2h")
        if not consensus:
            continue

        try:
            feats = await build_game_features(game.home_team, game.away_team, game.commence_time.date(), nba_client)
            home_model_prob = predictor.predict_home_win_prob(features_to_array(feats))
        except Exception as exc:
            logger.warning("Skipping model pick for %s vs %s: %s", game.home_team, game.away_team, exc)
            continue

        sides = {
            game.home_team: home_model_prob,
            game.away_team: 1 - home_model_prob,
        }

        for side, model_prob in sides.items():
            side_data = consensus.get(side)
            if not side_data:
                continue
            market_prob = side_data["fair_prob"]
            disagreement = abs(model_prob - market_prob)
            if disagreement < 0.03:
                continue

            ev = calculate_pick_ev(model_prob, side_data["best_odds"])
            if ev["ev_pct"] <= 0.01:
                continue

            steam = detect_steam_move(game.id, "h2h", side, snapshots)
            rlm = detect_reverse_line_movement(game.id, "h2h", side, snapshots)
            change = get_opening_to_current_change(game.id, "h2h", side, snapshots)
            signals = score_signals(
                ev_pct=ev["ev_pct"],
                steam=steam,
                rlm=rlm,
                opening_odds=change["opening_odds"],
                current_odds=change["current_odds"],
                is_outlier_book=side_data["is_outlier"],
                data_quality=dq,
            )
            signals_firing = int(signals.ev_positive + signals.steam_move + signals.reverse_line_movement + signals.best_line_available + signals.consensus_deviation)
            tier = assign_confidence(signals.composite, ev["ev_pct"], signals_firing, dq)
            if tier == ConfidenceTier.FILTERED:
                continue

            dec_odds = american_to_decimal(side_data["best_odds"])
            kelly = kelly_criterion(model_prob, dec_odds)
            latest_for_side = [s for s in snapshots if s.market == "h2h" and s.side == side]
            line = latest_for_side[-1].line if latest_for_side else None

            generated.append(
                Pick(
                    game_id=game.id,
                    sport_key=snapshots[-1].sport_key,
                    pick_date=today_start,
                    market="h2h",
                    side=side,
                    line=line,
                    odds_american=side_data["best_odds"],
                    best_book=side_data["best_book"] or "unknown",
                    fair_prob=model_prob,
                    prob_source="model_v1",
                    implied_prob=ev["implied_prob_at_best_odds"],
                    ev_pct=ev["ev_pct"],
                    composite_score=signals.composite,
                    confidence_tier=tier.value,
                    signals=signal_to_dict(signals),
                    data_quality=data_quality_to_dict(dq),
                    suggested_kelly_fraction=kelly,
                )
            )

    return generated


async def generate_daily_picks(session: AsyncSession) -> list[Pick]:
    now = datetime.now(UTC)
    window_end = now + timedelta(hours=24)

    games = (
        await session.scalars(
            select(Game).where(and_(Game.commence_time >= now, Game.commence_time <= window_end)).order_by(Game.commence_time)
        )
    ).all()
    if not games:
        return []

    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    await session.execute(delete(Pick).where(Pick.pick_date >= today_start))

    consensus_picks = await generate_consensus_picks(session, games, today_start)
    model_picks = await generate_model_picks(session, games, today_start)

    deduped: dict[tuple[int, str, str], Pick] = {}
    for pick in [*consensus_picks, *model_picks]:
        key = (pick.game_id, pick.market, pick.side)
        existing = deduped.get(key)
        if existing is None or pick.ev_pct > existing.ev_pct:
            deduped[key] = pick

    merged = sorted(deduped.values(), key=lambda p: p.ev_pct, reverse=True)
    top_picks = merged[:10]
    session.add_all(top_picks)
    await session.commit()
    return top_picks
