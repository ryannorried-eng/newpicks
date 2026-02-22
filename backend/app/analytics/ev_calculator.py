from __future__ import annotations

from app.utils.odds_math import american_to_decimal, american_to_implied_prob, calculate_ev


def calculate_pick_ev(fair_prob: float, best_odds_american: int) -> dict:
    decimal_odds = american_to_decimal(best_odds_american)
    implied = american_to_implied_prob(best_odds_american)
    ev_pct = calculate_ev(fair_prob, decimal_odds)
    return {
        "fair_prob": fair_prob,
        "best_odds": best_odds_american,
        "best_odds_decimal": decimal_odds,
        "implied_prob_at_best_odds": implied,
        "ev_pct": ev_pct,
        "edge": fair_prob - implied,
        "prob_source": "consensus",
    }
