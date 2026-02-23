import logging

import pytest

from app.services.odds_normalizer import resolve_side


def test_resolve_side_home_literal() -> None:
    assert resolve_side("home", "Chicago Bulls", "Miami Heat") == "home"


def test_resolve_side_away_literal_case_insensitive() -> None:
    assert resolve_side("Away", "Chicago Bulls", "Miami Heat") == "away"


def test_resolve_side_home_team_exact_match() -> None:
    assert resolve_side("Chicago Bulls", "Chicago Bulls", "Miami Heat") == "home"


def test_resolve_side_home_team_case_insensitive_match() -> None:
    assert resolve_side("chicago bulls", "Chicago Bulls", "Miami Heat") == "home"


def test_resolve_side_home_team_alias_match() -> None:
    assert resolve_side("Los Angeles Clippers", "LA Clippers", "Miami Heat") == "home"


def test_resolve_side_unknown_logs_warning(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING):
        resolved = resolve_side("???", "Chicago Bulls", "Miami Heat", snapshot_id=99)

    assert resolved is None
    assert "Could not resolve odds snapshot side" in caplog.text
