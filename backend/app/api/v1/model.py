from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.consensus import calculate_consensus
from app.data_providers.nba_stats import NBAStatsClient
from app.database import get_session
from app.ml.features import build_game_features, features_to_array, features_to_dict
from app.ml.model import predictor
from app.models.game import Game
from app.models.odds_snapshot import OddsSnapshot
from app.models.sport import Sport
from app.tasks.train_model import run_model_training_background

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/model", tags=["model"])


@router.get("/status")
async def model_status() -> dict:
    return {
        "is_trained": predictor.is_trained,
        "training_accuracy": predictor.training_accuracy,
        "cv_accuracy": predictor.cv_accuracy,
        "n_training_samples": predictor.n_training_samples,
        "last_trained": predictor.last_trained.isoformat() if predictor.last_trained else None,
        "top_features": predictor.top_features,
    }


@router.post("/train")
async def train_model() -> dict:
    client = NBAStatsClient()
    asyncio.create_task(run_model_training_background(client))
    return {"status": "training_started"}


@router.get("/predictions/today")
async def today_predictions(session: AsyncSession = Depends(get_session)) -> list[dict]:
    if not predictor.is_trained:
        return []

    nba_sport = await session.scalar(select(Sport).where(Sport.key == "basketball_nba"))
    if nba_sport is None:
        return []

    now = datetime.now(UTC)
    end = now + timedelta(days=1)
    games = (
        await session.scalars(
            select(Game).where(and_(Game.sport_id == nba_sport.id, Game.commence_time >= now, Game.commence_time <= end)).order_by(Game.commence_time)
        )
    ).all()

    client = NBAStatsClient()
    seasons = {g.commence_time.date().year for g in games}
    for season in seasons:
        if not await client.get_team_stats(season, use_cache=True):
            logger.info("Skipping /model/predictions/today: missing cached team stats for season %s", season)
            return []

    predictions: list[dict] = []

    for game in games:
        snapshots = (
            await session.scalars(
                select(OddsSnapshot).where(OddsSnapshot.game_id == game.id).order_by(OddsSnapshot.snapshot_time.asc())
            )
        ).all()
        if not snapshots:
            continue
        market = calculate_consensus(snapshots, "h2h")
        home_market = market.get(game.home_team, {}).get("fair_prob")
        if home_market is None:
            continue

        try:
            features = await build_game_features(game.home_team, game.away_team, game.commence_time.date(), client)
            model_prob = predictor.predict_home_win_prob(features_to_array(features))
        except Exception:
            continue

        predictions.append(
            {
                "game_id": game.id,
                "home_team": game.home_team,
                "away_team": game.away_team,
                "model_home_win_prob": model_prob,
                "market_home_win_prob": home_market,
                "disagreement_pct": abs(model_prob - home_market),
                "features": features_to_dict(features),
            }
        )

    return predictions
