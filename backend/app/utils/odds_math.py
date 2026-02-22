from __future__ import annotations

from math import prod


def american_to_decimal(american_odds: int) -> float:
    """Convert American odds to decimal. -110 -> 1.909, +150 -> 2.5"""
    if american_odds == 0:
        raise ValueError("American odds cannot be 0")
    if american_odds > 0:
        return round((american_odds / 100) + 1, 3)
    return round((100 / abs(american_odds)) + 1, 3)


def decimal_to_american(decimal_odds: float) -> int:
    """Convert decimal odds to American. 1.909 -> -110, 2.5 -> +150"""
    if decimal_odds <= 1:
        raise ValueError("Decimal odds must be greater than 1")
    if decimal_odds >= 2:
        return int(round((decimal_odds - 1) * 100))
    return int(round(-100 / (decimal_odds - 1)))


def american_to_implied_prob(american_odds: int) -> float:
    """Convert American odds to implied probability. -110 -> 0.5238"""
    if american_odds == 0:
        raise ValueError("American odds cannot be 0")
    if american_odds > 0:
        return 100 / (american_odds + 100)
    return abs(american_odds) / (abs(american_odds) + 100)


def implied_prob_to_american(prob: float) -> int:
    """Convert implied probability to American odds. 0.6 -> -150"""
    if prob <= 0 or prob >= 1:
        raise ValueError("Probability must be between 0 and 1")
    if prob >= 0.5:
        return int(round(-(prob / (1 - prob)) * 100))
    return int(round(((1 - prob) / prob) * 100))


def remove_vig(probs: list[float]) -> list[float]:
    """Normalize overround probabilities to sum to 1.0 (remove vig/juice)."""
    if not probs:
        return []
    if any(p < 0 for p in probs):
        raise ValueError("Probabilities must be non-negative")
    total = sum(probs)
    if total <= 0:
        raise ValueError("Sum of probabilities must be positive")
    return [p / total for p in probs]


def calculate_ev(fair_prob: float, decimal_odds: float) -> float:
    """EV% = (fair_prob * decimal_odds) - 1. Returns as decimal (0.05 = 5%)."""
    return (fair_prob * decimal_odds) - 1


def calculate_parlay_odds(decimal_odds_list: list[float]) -> float:
    """Product of decimal odds for all legs."""
    if not decimal_odds_list:
        raise ValueError("At least one leg is required")
    if any(odds <= 1 for odds in decimal_odds_list):
        raise ValueError("Each decimal odd must be greater than 1")
    return prod(decimal_odds_list)


def kelly_criterion(fair_prob: float, decimal_odds: float, fraction: float = 0.25) -> float:
    """Quarter-Kelly by default. Returns fraction of bankroll to wager. Never negative."""
    if not 0 < fair_prob < 1:
        raise ValueError("fair_prob must be between 0 and 1")
    if decimal_odds <= 1:
        raise ValueError("decimal_odds must be greater than 1")
    if fraction <= 0:
        raise ValueError("fraction must be positive")

    b = decimal_odds - 1
    q = 1 - fair_prob
    full_kelly = ((b * fair_prob) - q) / b
    return max(0.0, full_kelly * fraction)
