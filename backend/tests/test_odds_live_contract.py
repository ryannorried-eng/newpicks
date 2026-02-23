import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace

from app.api.v1.odds import live_odds


class _Result:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _FakeSession:
    def __init__(self, rows):
        self._rows = rows

    async def execute(self, _query):
        return _Result(self._rows)


def test_live_odds_includes_required_keys_and_totals_are_null():
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

    payload = asyncio.run(live_odds(session=_FakeSession(rows)))

    assert all("canonical_side" in row for row in payload)
    assert all("normalized_team" in row for row in payload)

    totals = next(row for row in payload if row["market"] == "totals")
    assert totals["canonical_side"] is None
    assert totals["normalized_team"] is None
