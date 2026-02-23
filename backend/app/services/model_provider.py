from __future__ import annotations

import logging
from datetime import date

from app.data_providers.nba_stats import NBAStatsClient
from app.ml.features import build_game_features, features_to_array
from app.ml.model import predictor
from app.models.game import Game

logger = logging.getLogger(__name__)


class ModelProvider:
    def __init__(self) -> None:
        self.nba_client = NBAStatsClient()

    async def get_true_prob(
        self,
        *,
        sport_key: str,
        game: Game,
        market: str,
        side: str,
        line: float | None,
        context: dict | None = None,
    ) -> float | None:
        if sport_key != "basketball_nba" or market != "h2h":
            return None
        if not predictor.is_trained:
            # TODO: load deployed model artifacts for more sports and markets.
            return None

        season = game.commence_time.year - 1 if game.commence_time.month < 10 else game.commence_time.year
        has_stats = await self.nba_client.get_team_stats(season, use_cache=True)
        if not has_stats:
            return None

        try:
            features = await build_game_features(game.home_team, game.away_team, game.commence_time.date(), self.nba_client)
            home_prob = predictor.predict_home_win_prob(features_to_array(features))
        except Exception as exc:
            logger.warning("model provider failed for game_id=%s side=%s: %s", game.id, side, exc)
            return None

        if side == game.home_team:
            return float(home_prob)
        if side == game.away_team:
            return float(1 - home_prob)
        return None


model_provider = ModelProvider()
