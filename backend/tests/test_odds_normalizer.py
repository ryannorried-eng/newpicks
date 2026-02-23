import logging

from app.services.odds_normalizer import normalize_team, resolve_side


def test_resolve_side_home_literal():
    assert resolve_side("home", "Boston Celtics", "Miami Heat") == "home"


def test_resolve_side_away_literal():
    assert resolve_side("away", "Boston Celtics", "Miami Heat") == "away"


def test_resolve_side_matches_home_team_case_insensitive():
    assert resolve_side("boston celtics", "Boston Celtics", "Miami Heat") == "home"


def test_resolve_side_matches_away_team_case_insensitive():
    assert resolve_side("MIAMI HEAT", "Boston Celtics", "Miami Heat") == "away"


def test_resolve_side_trims_whitespace():
    assert resolve_side("  Boston Celtics  ", "Boston Celtics", "Miami Heat") == "home"


def test_resolve_side_unknown_returns_none_and_logs_warning(caplog):
    caplog.set_level(logging.WARNING)

    assert resolve_side("draw", "Boston Celtics", "Miami Heat") is None
    assert "Could not resolve side 'draw'" in caplog.text


def test_normalize_team_returns_home_team_for_home_side():
    assert normalize_team("home", "Boston Celtics", "Miami Heat") == "Boston Celtics"


def test_normalize_team_returns_none_for_unknown_side():
    assert normalize_team("draw", "Boston Celtics", "Miami Heat") is None
