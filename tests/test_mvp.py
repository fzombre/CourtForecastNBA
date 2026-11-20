"""Checks for the MVP race (src/mvp.py).

The model tests use the real history file (data/mvp_history.csv, committed to git);
the race tests use the made-up schedule and players, so nothing here needs the internet.
"""
import random

import numpy as np
import pandas as pd
import pytest

import mvp
from data import TEAMS, parse_games
from forecast import build_forecast
from players import parse_player_stats
from tests.fake_players import INJURED_ID, STAR_ID, fake_players
from tests.fake_schedule import fake_schedule


@pytest.fixture(scope="module")
def history():
    return mvp.load_history()


@pytest.fixture(scope="module")
def race(history):
    """The whole race on made-up data: 300 simulated seasons is plenty for these checks."""
    games, _ = parse_games(fake_schedule())
    players = parse_player_stats(fake_players())
    forecast = build_forecast(games, n_sims=300, seed=0)
    return mvp.mvp_race(mvp.train(history), players, games, forecast["season_wins"], history=history, seed=0)


def test_history_has_exactly_one_mvp_per_season(history):
    per_season = history.groupby("season")["mvp"].sum()
    assert list(per_season.index) == list(mvp.MVP_WINNERS)   # every season, in order
    assert (per_season == 1).all()
    # The training pool's filters must never drop a real MVP.
    assert mvp.training_pool(history)["mvp"].sum() == len(mvp.MVP_WINNERS)


def test_softmax_adds_up_inside_each_group():
    scores = np.array([1.0, 2.0, 3.0, 0.5, 0.5, 800.0])   # 800: would overflow without the max trick
    groups = np.array([0, 0, 0, 1, 1, 2])
    chances = mvp.softmax_by_group(scores, groups)
    assert np.allclose(np.bincount(groups, weights=chances), 1.0)
    assert chances[2] > chances[1] > chances[0]             # higher score, bigger slice
    assert chances[3] == pytest.approx(0.5)                  # equal scores, equal slices


def test_model_finds_past_mvps(history):
    # When the model was written it picked 16 of 30 past MVPs, with 28 in its top 3.
    # These floors leave a little room, but catch a change that breaks the model.
    result = mvp.backtest(history)
    assert result["seasons"] == len(mvp.MVP_WINNERS)
    assert result["top1"] >= 14
    assert result["top3"] >= 26
    # Every weight should point the way voters do: more points, wins, etc. = better.
    assert (mvp.train(history)["weights"] > 0).all()


def test_race_chances_add_up(race):
    assert race["chance"].sum() == pytest.approx(100, abs=0.01)   # exactly one MVP per simulated season
    assert race["today"].sum() == pytest.approx(100, abs=0.01)    # the ladder is one "season" too
    assert race["chance"].is_monotonic_decreasing                  # best chance first
    ranks = race["rank"].dropna().sort_values()
    assert list(ranks) == list(range(1, len(ranks) + 1))           # ladder ranks 1, 2, 3, ... with no gaps


def test_race_favors_the_star_and_drops_the_injured_star(race):
    assert race.iloc[0]["player_id"] == STAR_ID
    assert race.iloc[0]["rank"] == 1
    # Missed too many games to ever reach the required number: not a candidate at all.
    assert INJURED_ID not in set(race["player_id"])
    assert (race["can_miss"] >= 0).all()


def test_team_games_counts_a_full_nba_season_as_82():
    # NBA.com lists 80 games per team until December (the NBA Cup adds the last 2).
    # Build 80 rounds in which every team plays exactly once.
    rng = random.Random(0)
    rows = []
    for _ in range(80):
        order = TEAMS[:]
        rng.shuffle(order)
        for i in range(0, 30, 2):
            rows.append({"stage": "Regular Season", "home": order[i], "away": order[i + 1],
                         "played": False, "winner": None})
    teams = mvp.team_games(pd.DataFrame(rows))
    assert (teams["scheduled"] == 80).all()
    assert (teams["total"] == 82).all()
    assert (teams["left"] == 82).all() and (teams["scheduled_left"] == 80).all()

    # The tests' made-up schedule is much shorter than an NBA season: taken as it is.
    short = mvp.team_games(parse_games(fake_schedule())[0])
    assert (short["total"] == short["scheduled"]).all()
