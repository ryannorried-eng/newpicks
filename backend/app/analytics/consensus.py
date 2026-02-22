from __future__ import annotations

from collections import defaultdict
from statistics import mean, pstdev
from typing import Any

from app.analytics.data_quality import SHARP_BOOKS
from app.utils.odds_math import american_to_decimal, decimal_to_american


def calculate_consensus(snapshots_for_game: list[Any], market: str) -> dict[str, dict[str, Any]]:
    filtered = [s for s in snapshots_for_game if s.market == market]
    by_side: dict[str, list[Any]] = defaultdict(list)
    for snap in filtered:
        by_side[snap.side].append(snap)

    result: dict[str, dict[str, Any]] = {}
    for side, snaps in by_side.items():
        weighted_probs = []
        raw_probs = []
        best_decimal = -1.0
        best_american = None
        best_book = None

        for s in snaps:
            weight = 2 if s.bookmaker in SHARP_BOOKS else 1
            weighted_probs.extend([float(s.no_vig_prob)] * weight)
            raw_probs.append(float(s.no_vig_prob))

            dec = american_to_decimal(int(s.odds))
            if dec > best_decimal:
                best_decimal = dec
                best_american = int(s.odds)
                best_book = s.bookmaker

        fair_prob = mean(weighted_probs) if weighted_probs else 0.0
        stdev = pstdev(raw_probs) if len(raw_probs) > 1 else 0.0
        outlier_books = []
        if stdev > 0:
            for s in snaps:
                if abs(float(s.no_vig_prob) - fair_prob) > (2 * stdev):
                    outlier_books.append(s.bookmaker)

        result[side] = {
            "fair_prob": fair_prob,
            "best_odds": best_american if best_american is not None else decimal_to_american(2.0),
            "best_book": best_book,
            "is_outlier": bool(outlier_books),
            "outlier_books": sorted(set(outlier_books)),
            "books_in_consensus": len({s.bookmaker for s in snaps}),
            "prob_source": "consensus",
        }

    return result
