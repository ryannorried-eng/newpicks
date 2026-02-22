from __future__ import annotations

from enum import Enum

from app.analytics.data_quality import DataQuality


class ConfidenceTier(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    FILTERED = "filtered"


def _downgrade_one_tier(tier: ConfidenceTier) -> ConfidenceTier:
    if tier == ConfidenceTier.HIGH:
        return ConfidenceTier.MEDIUM
    if tier == ConfidenceTier.MEDIUM:
        return ConfidenceTier.LOW
    return tier


def assign_confidence(
    composite_score: float,
    ev_pct: float,
    signals_firing: int,
    data_quality: DataQuality,
) -> ConfidenceTier:
    adjusted_composite = composite_score - (0.10 if not data_quality.sharp_books_present else 0.0)

    if adjusted_composite >= 0.70 and ev_pct >= 0.05 and signals_firing >= 3:
        tier = ConfidenceTier.HIGH
    elif adjusted_composite >= 0.45 and ev_pct >= 0.02 and signals_firing >= 2:
        tier = ConfidenceTier.MEDIUM
    elif adjusted_composite >= 0.30 and ev_pct >= 0.01:
        tier = ConfidenceTier.LOW
    else:
        return ConfidenceTier.FILTERED

    if data_quality.books_covered < 4 and tier == ConfidenceTier.HIGH:
        tier = ConfidenceTier.MEDIUM
    if data_quality.snapshot_freshness_minutes > 120:
        tier = ConfidenceTier.LOW if tier != ConfidenceTier.FILTERED else tier
    if data_quality.line_dispersion > 0.06:
        tier = _downgrade_one_tier(tier)
    if data_quality.market_completeness < 0.66:
        tier = _downgrade_one_tier(tier)

    return tier
