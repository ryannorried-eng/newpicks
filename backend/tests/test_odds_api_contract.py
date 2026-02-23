from datetime import datetime, timezone
from types import SimpleNamespace

from app.services.odds_normalizer import format_live_odds_rows


def test_live_odds_contract_includes_canonical_side_and_normalized_team_keys():
    snapshot_time = datetime.now(timezone.utc)
    rows = [
        (
            SimpleNamespace(
                game_id=1,
                sport_key="basketball_nba",
                bookmaker="book_a",
                market="h2h",
                side="Boston Celtics",
                odds=-110,
                line=None,
                snapshot_time=snapshot_time,
            ),
            "Boston Celtics",
            "Miami Heat",
        ),
        (
            SimpleNamespace(
                game_id=1,
                sport_key="basketball_nba",
                bookmaker="book_a",
                market="totals",
                side="over",
                odds=-105,
                line=219.5,
                snapshot_time=snapshot_time,
            ),
            "Boston Celtics",
            "Miami Heat",
        ),
    ]

    payload = format_live_odds_rows(rows)

    assert all("canonical_side" in row for row in payload)
    assert all("normalized_team" in row for row in payload)

    h2h = next(row for row in payload if row["market"] == "h2h")
    totals = next(row for row in payload if row["market"] == "totals")

    assert h2h["canonical_side"] == "home"
    assert h2h["normalized_team"] == "Boston Celtics"
    assert totals["canonical_side"] is None
    assert totals["normalized_team"] is None
