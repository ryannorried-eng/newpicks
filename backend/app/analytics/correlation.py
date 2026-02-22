from __future__ import annotations

import math

CORRELATION_PRIORS: dict[tuple[str, str, str, str], float] = {
    ("h2h", "home", "h2h", "away"): -1.0,
    ("h2h", "home", "spreads", "home"): 0.90,
    ("h2h", "away", "spreads", "away"): 0.90,
    ("h2h", "home", "spreads", "away"): -0.90,
    ("h2h", "away", "spreads", "home"): -0.90,
    ("h2h", "home", "totals", "over"): 0.30,
    ("h2h", "home", "totals", "under"): -0.20,
    ("h2h", "away", "totals", "over"): 0.25,
    ("h2h", "away", "totals", "under"): -0.15,
    ("spreads", "home", "totals", "over"): 0.15,
    ("spreads", "home", "totals", "under"): -0.10,
    ("spreads", "away", "totals", "over"): 0.10,
    ("spreads", "away", "totals", "under"): -0.05,
    ("totals", "over", "totals", "under"): -1.0,
    ("spreads", "home", "spreads", "away"): -1.0,
}

CROSS_GAME_SAME_SPORT = 0.02
CROSS_GAME_CROSS_SPORT = 0.00


def _get_value(pick, key: str):
    return pick[key] if isinstance(pick, dict) else getattr(pick, key)


def estimate_correlation(pick_a, pick_b) -> float:
    game_a = _get_value(pick_a, "game_id")
    game_b = _get_value(pick_b, "game_id")
    sport_a = _get_value(pick_a, "sport_key")
    sport_b = _get_value(pick_b, "sport_key")

    if game_a != game_b:
        return CROSS_GAME_SAME_SPORT if sport_a == sport_b else CROSS_GAME_CROSS_SPORT

    market_a = _get_value(pick_a, "market")
    side_a = _get_value(pick_a, "side")
    market_b = _get_value(pick_b, "market")
    side_b = _get_value(pick_b, "side")

    key = (market_a, side_a, market_b, side_b)
    rev_key = (market_b, side_b, market_a, side_a)
    if key in CORRELATION_PRIORS:
        return CORRELATION_PRIORS[key]
    if rev_key in CORRELATION_PRIORS:
        return CORRELATION_PRIORS[rev_key]
    return 0.10


def adjusted_joint_probability(prob_a: float, prob_b: float, correlation: float) -> float:
    value = (prob_a * prob_b) + correlation * math.sqrt(prob_a * (1 - prob_a) * prob_b * (1 - prob_b))
    return max(0.0, min(1.0, value))
