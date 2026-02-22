from app.analytics.correlation import adjusted_joint_probability, estimate_correlation


def pick(**kwargs):
    base = {"game_id": 1, "market": "h2h", "side": "home", "sport_key": "basketball_nba"}
    base.update(kwargs)
    return base


def test_same_game_ml_home_spread_home():
    corr = estimate_correlation(pick(market="h2h", side="home"), pick(market="spreads", side="home"))
    assert round(corr, 2) == 0.90


def test_same_game_ml_home_total_over():
    corr = estimate_correlation(pick(market="h2h", side="home"), pick(market="totals", side="over"))
    assert round(corr, 2) == 0.30


def test_cross_game_same_sport():
    corr = estimate_correlation(pick(game_id=1), pick(game_id=2))
    assert round(corr, 2) == 0.02


def test_cross_sport():
    corr = estimate_correlation(pick(sport_key="basketball_nba"), pick(game_id=2, sport_key="americanfootball_nfl"))
    assert round(corr, 2) == 0.00


def test_joint_probability_positive_corr_higher_than_independent():
    p = adjusted_joint_probability(0.55, 0.60, 0.30)
    assert p > (0.55 * 0.60)


def test_joint_probability_negative_corr_lower_than_independent():
    p = adjusted_joint_probability(0.55, 0.60, -0.30)
    assert p < (0.55 * 0.60)
