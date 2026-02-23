import logging

from app.services.odds_normalizer import normalize_team_name, resolve_side


def test_resolve_side_home_literal_mapping():
    assert resolve_side("HoMe", "Boston Celtics", "Miami Heat") == "home"


def test_resolve_side_away_literal_mapping():
    assert resolve_side("AWAY", "Boston Celtics", "Miami Heat") == "away"


def test_resolve_side_team_name_case_and_whitespace_mapping():
    assert resolve_side("  boston    celtics ", "Boston Celtics", "Miami Heat") == "home"
    assert resolve_side(" miami    HEAT", "Boston Celtics", "Miami Heat") == "away"


def test_resolve_side_unknown_returns_none_and_logs_warning(caplog):
    caplog.set_level(logging.WARNING)

    assert resolve_side("draw", "Boston Celtics", "Miami Heat") is None
    assert "Could not resolve side 'draw'" in caplog.text


def test_normalize_team_name_collapses_case_and_whitespace():
    assert normalize_team_name("  Boston   CELTICS ") == "boston celtics"
    assert normalize_team_name(None) is None
