import model
from data import parse_games, standings
from forecast import build_forecast
from tests.fake_schedule import fake_schedule


def test_parse_and_standings():
    games, season = parse_games(fake_schedule())
    assert season == "2026-27"
    assert games["played"].sum() == 350
    table = standings(games)
    assert table["W"].sum() == table["L"].sum() == 350


def test_elo_probability_favors_home_when_equal():
    assert 0.5 < model.elo_win_probability(0) < 0.65


def test_forecast_odds_add_up():
    games, _ = parse_games(fake_schedule())
    result = build_forecast(games, n_sims=300, seed=0)
    odds = result["odds"]
    assert abs(odds["champion"].sum() - 100) < 0.5        # exactly one champion per season
    assert abs(odds["finals"].sum() - 200) < 0.5          # two finalists
    assert abs(odds["playoffs"].sum() - 1600) < 0.5       # 16 playoff teams
    assert result["upcoming"]["home_win_prob"].between(0, 1).all()
