import pytest

from app.utils.odds_math import (
    american_to_decimal,
    american_to_implied_prob,
    calculate_ev,
    calculate_parlay_odds,
    decimal_to_american,
    implied_prob_to_american,
    kelly_criterion,
    remove_vig,
)


def test_american_decimal_roundtrip_even_money():
    assert american_to_decimal(100) == 2.0
    assert decimal_to_american(2.0) == 100


def test_heavy_favorite_and_huge_dog():
    assert american_to_decimal(-500) == 1.2
    assert american_to_decimal(1000) == 11.0


def test_implied_prob_conversions():
    assert round(american_to_implied_prob(-110), 4) == 0.5238
    assert implied_prob_to_american(0.6) == -150


def test_remove_vig_normalizes():
    out = remove_vig([0.55, 0.50])
    assert round(sum(out), 10) == 1.0


def test_calculate_ev_and_parlay_odds():
    assert round(calculate_ev(0.45, 2.5), 4) == 0.125
    assert round(calculate_parlay_odds([1.91, 2.1]), 4) == 4.011


def test_kelly_never_negative():
    assert kelly_criterion(0.40, 2.0) == 0.0


def test_invalid_inputs():
    with pytest.raises(ValueError):
        american_to_decimal(0)
    with pytest.raises(ValueError):
        implied_prob_to_american(1.0)
    with pytest.raises(ValueError):
        calculate_parlay_odds([])
