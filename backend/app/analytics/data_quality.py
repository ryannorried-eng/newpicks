from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from statistics import pstdev
from typing import Any

SHARP_BOOKS = {"pinnacle", "betonlineag", "bovada", "circa"}
EXPECTED_MARKETS = {"h2h", "spreads", "totals"}


@dataclass
class DataQuality:
    books_covered: int
    snapshot_freshness_minutes: int
    sharp_books_present: bool
    line_dispersion: float
    market_completeness: float


def assess_game_quality(game_id: int, snapshots: list[Any]) -> DataQuality:
    if not snapshots:
        return DataQuality(0, 9999, False, 0.0, 0.0)

    books = {s.bookmaker for s in snapshots}
    latest = max(s.snapshot_time for s in snapshots if s.snapshot_time is not None)
    now = datetime.now(UTC)
    freshness = int(max(0.0, (now - latest).total_seconds() / 60))

    probs = [float(s.no_vig_prob) for s in snapshots if s.no_vig_prob is not None]
    dispersion = float(pstdev(probs)) if len(probs) > 1 else 0.0

    markets = {s.market for s in snapshots}
    completeness = len(markets & EXPECTED_MARKETS) / len(EXPECTED_MARKETS)

    sharp_present = any(book in SHARP_BOOKS for book in books)

    return DataQuality(
        books_covered=len(books),
        snapshot_freshness_minutes=freshness,
        sharp_books_present=sharp_present,
        line_dispersion=dispersion,
        market_completeness=completeness,
    )


def data_quality_to_dict(data_quality: DataQuality) -> dict[str, Any]:
    return asdict(data_quality)
