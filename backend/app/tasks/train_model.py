from __future__ import annotations

import asyncio
import json
import logging
import os
import pickle
from datetime import UTC, datetime
from typing import Any

import numpy as np
from sqlalchemy import and_, select

from app.data_providers.nba_stats import NBAStatsClient, TEAM_STATS_CACHE_PATH
from app.database import AsyncSessionLocal
from app.ml.features import build_game_features, features_to_array
from app.ml.model import predictor
from app.models.game import Game
from app.models.sport import Sport

CACHE_PATH = os.environ.get("TRAINING_CACHE_PATH", "/app/models/nba_training_cache.pkl")
logger = logging.getLogger(__name__)

def _write_team_stats_cache(season: int, stats: list[dict[str, Any]]) -> None:
    if not stats:
        return

    team_stats_by_name: dict[str, dict[str, Any]] = {}
    for team_stats in stats:
        team_name = str(team_stats.get("team_name", "")).strip()
        if not team_name:
            continue
        team_stats_by_name[team_name] = team_stats

    if not team_stats_by_name:
        return

    os.makedirs(os.path.dirname(TEAM_STATS_CACHE_PATH), exist_ok=True)

    with open(TEAM_STATS_CACHE_PATH, "w", encoding="utf-8") as file:
        json.dump(team_stats_by_name, file)

    logger.info("Saved team stats cache with %s teams", len(team_stats_by_name))


async def collect_training_data(
    nba_client: NBAStatsClient,
    seasons: list[int] = [2024, 2025],
) -> tuple[np.ndarray, np.ndarray]:
    os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
    if os.path.exists(CACHE_PATH):
        logger.info("Loading cached training data from %s", CACHE_PATH)
        with open(CACHE_PATH, "rb") as file:
            cached = pickle.load(file)
        return np.array(cached["X"]), np.array(cached["y"])

    X: list[list[float]] = []
    y: list[int] = []

    for season in seasons:
        season_stats = await nba_client.get_team_stats(season, use_cache=False)
        _write_team_stats_cache(season, season_stats)

    async with AsyncSessionLocal() as session:
        nba_sport = await session.scalar(select(Sport).where(Sport.key == "basketball_nba"))
        if nba_sport is not None:
            games = (
                await session.scalars(
                    select(Game).where(
                        and_(Game.sport_id == nba_sport.id, Game.completed.is_(True), Game.home_score.is_not(None), Game.away_score.is_not(None))
                    )
                )
            ).all()
            logger.info("Found %s completed NBA games in database for training", len(games))
            for idx, game in enumerate(games, start=1):
                try:
                    logger.info("Building features from DB game %s of %s (%s vs %s)", idx, len(games), game.home_team, game.away_team)
                    features = await build_game_features(game.home_team, game.away_team, game.commence_time.date(), nba_client)
                except Exception:
                    logger.exception("Failed to build features for DB game %s", game.id)
                    continue
                X.append(features_to_array(features))
                y.append(1 if (game.home_score or 0) > (game.away_score or 0) else 0)

    if X:
        logger.info("Collected %s samples from database", len(X))

    if not X:
        logger.info("No DB training data found; collecting via season game endpoints")
        await nba_client._load_teams()
        for season in seasons:
            logger.info("Fetching season %s games...", season)
            season_games = await nba_client.get_season_games(season)
            if not season_games:
                logger.warning("No season game rows returned for %s", season)
                continue

            # keep one row per GAME_ID (home team row) to avoid duplicates
            grouped_games: dict[str, dict[str, Any]] = {}
            for row in season_games:
                game_id = str(row.get("GAME_ID", "")).strip()
                if not game_id:
                    continue
                matchup = str(row.get("MATCHUP", ""))
                if " vs. " in matchup:
                    grouped_games[game_id] = row
                elif game_id not in grouped_games:
                    grouped_games[game_id] = row

            games = list(grouped_games.values())
            logger.info("Got %s unique games for season %s", len(games), season)

            for idx, game in enumerate(games, start=1):
                home_team = str(game.get("TEAM_NAME", ""))
                matchup = str(game.get("MATCHUP", ""))
                away_abbr = matchup.split()[-1] if matchup else ""
                if not home_team or not away_abbr:
                    continue

                away_team = next(
                    (t["team_name"] for t in nba_client._team_cache.values() if t["abbreviation"] == away_abbr),
                    "",
                )
                if not away_team:
                    continue

                game_date_val = game.get("GAME_DATE")
                if game_date_val is None:
                    continue
                if hasattr(game_date_val, "date"):
                    game_date = game_date_val.date()
                else:
                    game_date = datetime.fromisoformat(str(game_date_val)).date()

                logger.info("Building features for game %s of %s (%s vs %s)", idx, len(games), home_team, away_team)
                try:
                    features = await build_game_features(home_team, away_team, game_date, nba_client)
                except Exception:
                    logger.exception("Failed feature build for %s vs %s", home_team, away_team)
                    continue

                X.append(features_to_array(features))
                y.append(1 if str(game.get("WL", "")).upper() == "W" else 0)

    logger.info("Collected %s total samples", len(X))
    with open(CACHE_PATH, "wb") as file:
        pickle.dump({"X": X, "y": y, "cached_at": datetime.now(UTC).isoformat()}, file)

    return np.array(X), np.array(y)


async def run_model_training(nba_client: NBAStatsClient) -> dict:
    logger.info("Starting model training pipeline")
    try:
        X, y = await collect_training_data(nba_client)
        if len(y) < 100:
            logger.warning("Insufficient training data: %s samples", len(y))
            return {"status": "insufficient_data", "n_samples": int(len(y)), "message": "Need at least 100 games to train model"}

        logger.info("Training model on %s samples...", len(y))
        report = predictor.train(X, y)
        logger.info("Model training completed")
        return {"status": "trained", **report}
    except Exception:
        logger.exception("Model training pipeline failed")
        return {"status": "failed", "message": "Training pipeline crashed; check backend logs"}


async def run_model_training_background(nba_client: NBAStatsClient) -> None:
    result = await run_model_training(nba_client)
    logger.info("Background training finished with status=%s", result.get("status"))
