from __future__ import annotations

from dataclasses import asdict, dataclass

from app.analytics.data_quality import DataQuality

SIGNAL_WEIGHTS = {
    "ev_positive": 0.25,
    "steam_move": 0.20,
    "reverse_line_movement": 0.15,
    "best_line_available": 0.10,
    "consensus_deviation": 0.10,
    "closing_line_trend": 0.10,
    "data_quality": 0.10,
}


@dataclass
class SignalBreakdown:
    ev_positive: float
    ev_magnitude: float
    steam_move: float
    reverse_line_movement: float
    best_line_available: float
    consensus_deviation: float
    closing_line_trend: float
    data_quality_score: float
    composite: float


def _quality_score(data_quality: DataQuality) -> float:
    score = 1.0
    if data_quality.books_covered < 4:
        score -= 0.2
    if data_quality.snapshot_freshness_minutes > 120:
        score -= 0.3
    if data_quality.line_dispersion > 0.06:
        score -= 0.2
    if data_quality.market_completeness < 0.66:
        score -= 0.2
    if not data_quality.sharp_books_present:
        score -= 0.1
    return max(0.0, min(1.0, score))


def score_signals(
    ev_pct: float,
    steam: dict | None,
    rlm: dict | None,
    opening_odds: int,
    current_odds: int,
    is_outlier_book: bool,
    data_quality: DataQuality,
) -> SignalBreakdown:
    ev_positive = 1.0 if ev_pct > 0 else 0.0
    steam_move = 1.0 if steam else 0.0
    reverse_line_movement = 1.0 if rlm else 0.0
    best_line_available = 1.0 if current_odds > opening_odds else 0.0
    consensus_deviation = 1.0 if is_outlier_book else 0.0
    closing_line_trend = 0.5
    data_quality_score = _quality_score(data_quality)

    composite = (
        (ev_positive * SIGNAL_WEIGHTS["ev_positive"])
        + (steam_move * SIGNAL_WEIGHTS["steam_move"])
        + (reverse_line_movement * SIGNAL_WEIGHTS["reverse_line_movement"])
        + (best_line_available * SIGNAL_WEIGHTS["best_line_available"])
        + (consensus_deviation * SIGNAL_WEIGHTS["consensus_deviation"])
        + (closing_line_trend * SIGNAL_WEIGHTS["closing_line_trend"])
        + (data_quality_score * SIGNAL_WEIGHTS["data_quality"])
    )

    return SignalBreakdown(
        ev_positive=ev_positive,
        ev_magnitude=ev_pct,
        steam_move=steam_move,
        reverse_line_movement=reverse_line_movement,
        best_line_available=best_line_available,
        consensus_deviation=consensus_deviation,
        closing_line_trend=closing_line_trend,
        data_quality_score=data_quality_score,
        composite=composite,
    )


def signal_to_dict(signal: SignalBreakdown) -> dict:
    return asdict(signal)
