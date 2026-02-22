from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from app.analytics.data_quality import assess_game_quality


def _snap(book, market, no_vig, mins_ago):
    return SimpleNamespace(
        bookmaker=book,
        market=market,
        no_vig_prob=no_vig,
        snapshot_time=datetime.now(UTC) - timedelta(minutes=mins_ago),
    )


def test_assess_game_quality_metrics():
    snapshots = [
        _snap("pinnacle", "h2h", 0.52, 5),
        _snap("draftkings", "h2h", 0.50, 4),
        _snap("fanduel", "spreads", 0.49, 3),
        _snap("betmgm", "totals", 0.51, 2),
    ]

    dq = assess_game_quality(1, snapshots)

    assert dq.books_covered == 4
    assert dq.snapshot_freshness_minutes >= 0
    assert dq.sharp_books_present is True
    assert dq.market_completeness == 1.0


def test_assess_game_quality_empty():
    dq = assess_game_quality(1, [])
    assert dq.books_covered == 0
    assert dq.market_completeness == 0.0
    assert dq.sharp_books_present is False
