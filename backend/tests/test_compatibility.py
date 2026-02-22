from app.analytics.compatibility import check_compatibility


def leg(**kwargs):
    base = {
        "game_id": 1,
        "market": "h2h",
        "side": "home",
        "home_team": "A",
        "away_team": "B",
        "sport_key": "basketball_nba",
    }
    base.update(kwargs)
    return base


def test_same_game_ml_spread_same_team_blocked():
    r = check_compatibility(leg(market="h2h", side="home"), leg(market="spreads", side="home"), "aggressive")
    assert r.is_compatible is False


def test_same_game_ml_total_allowed_mod_aggressive_blocked_conservative():
    a = leg(market="h2h", side="home")
    b = leg(market="totals", side="over")
    assert check_compatibility(a, b, "conservative").is_compatible is False
    assert check_compatibility(a, b, "moderate").is_compatible is True
    assert check_compatibility(a, b, "aggressive").is_compatible is True


def test_cross_game_always_allowed():
    r = check_compatibility(leg(game_id=1), leg(game_id=2), "conservative")
    assert r.is_compatible is True


def test_same_game_opposing_ml_blocked():
    r = check_compatibility(leg(market="h2h", side="home"), leg(market="h2h", side="away"), "aggressive")
    assert r.is_compatible is False
