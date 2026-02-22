from __future__ import annotations

from dataclasses import dataclass

from app.analytics.correlation import estimate_correlation

CORRELATION_CEILINGS = {
    "conservative": 0.15,
    "moderate": 0.40,
    "aggressive": 0.70,
}


@dataclass
class CompatibilityResult:
    is_compatible: bool
    reason: str


def _get_value(leg, key: str):
    return leg[key] if isinstance(leg, dict) else getattr(leg, key)


def check_compatibility(leg_a, leg_b, risk_level: str) -> CompatibilityResult:
    game_a = _get_value(leg_a, "game_id")
    game_b = _get_value(leg_b, "game_id")

    if game_a != game_b:
        return CompatibilityResult(True, "")

    market_a = _get_value(leg_a, "market")
    market_b = _get_value(leg_b, "market")
    side_a = _get_value(leg_a, "side")
    side_b = _get_value(leg_b, "side")

    # 1) same game + same market
    if market_a == market_b:
        # 3) same game + opposing side same market is also always blocked
        if side_a != side_b:
            return CompatibilityResult(False, "same_game_opposing_sides_same_market")
        return CompatibilityResult(False, "same_game_same_market")

    # 2) same game + same team related markets (ML + spread)
    if {market_a, market_b} == {"h2h", "spreads"} and side_a == side_b:
        return CompatibilityResult(False, "same_game_same_team_related_markets")

    corr = estimate_correlation(leg_a, leg_b)
    if corr > CORRELATION_CEILINGS[risk_level]:
        return CompatibilityResult(False, f"correlation_above_ceiling:{corr:.2f}")

    return CompatibilityResult(True, "")
