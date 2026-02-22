from __future__ import annotations

import asyncio
import os
import pickle
from datetime import UTC, datetime

import numpy as np
from sqlalchemy import and_, select

from app.data_providers.nba_stats import NBAStatsClient
from app.database import AsyncSessionLocal
from app.ml.features import build_game_features, features_to_array
from app.ml.model import predictor
from app.models.game import Game
from app.models.sport import Sport

CACHE_PATH = os.environ.get("TRAINING_CACHE_PATH", "/app/models/nba_training_cache.pkl")


async def collect_training_data(
    nba_client: NBAStatsClient,
    seasons: list[int] = [2024, 2025],
) -> tuple[np.ndarray, np.ndarray]:
    os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
    if os.path.exists(CACHE_PATH):
        with open(CACHE_PATH, "rb") as file:
            cached = pickle.load(file)
        return np.array(cached["X"]), np.array(cached["y"])

    X: list[list[float]] = []
    y: list[int] = []

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
            for game in games:
                try:
                    features = await build_game_features(game.home_team, game.away_team, game.commence_time.date(), nba_client)
                except Exception:
                    continue
                X.append(features_to_array(features))
                y.append(1 if (game.home_score or 0) > (game.away_score or 0) else 0)

    if not X:
        for season in seasons:
            team_stats = await nba_client.get_team_stats(season)
            for team in team_stats:
                await asyncio.sleep(0.6)
                recent = await nba_client.get_recent_games(team["team_id"], n_games=10)
                for game in recent:
                    opp = next((t for t in team_stats if t["team_name"] == game["opponent"]), None)
                    if not opp:
                        continue
                    home = team if game["home"] else opp
                    away = opp if game["home"] else team
                    fake_date = datetime.now(UTC).date()
                    try:
                        features = await build_game_features(home["team_name"], away["team_name"], fake_date, nba_client)
                    except Exception:
                        continue
                    X.append(features_to_array(features))
                    y.append(1 if game["win"] == game["home"] else 0)

    with open(CACHE_PATH, "wb") as file:
        pickle.dump({"X": X, "y": y, "cached_at": datetime.now(UTC).isoformat()}, file)

    return np.array(X), np.array(y)


async def run_model_training(nba_client: NBAStatsClient) -> dict:
    X, y = await collect_training_data(nba_client)
    if len(y) < 20:
        return {"status": "insufficient_data", "n_samples": int(len(y))}

    report = predictor.train(X, y)
    return {"status": "trained", **report}
