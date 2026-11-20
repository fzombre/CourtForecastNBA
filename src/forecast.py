"""Glue: runs steps 1-3 in order and hands the results to the app.

  games table (data.py)
     -> features + trained model (model.py)
     -> win probability for every upcoming game
     -> Monte Carlo season + playoffs (simulate.py)
"""
import pandas as pd

import model
import simulate
from data import TEAMS, standings


def build_forecast(games, n_sims=2000, seed=None):
    games = model.add_rest_days(games)

    # Step 2: learn from finished games, then score upcoming ones.
    training, ratings = model.replay_season(games)
    trained = model.train_model(training)
    upcoming = model.features_for_upcoming(games, ratings)
    upcoming["home_win_prob"] = model.predict(trained, upcoming) if len(upcoming) else []
    upcoming["predicted_winner"] = upcoming["home"].where(upcoming["home_win_prob"] >= 0.5, upcoming["away"])
    upcoming["confidence"] = upcoming["home_win_prob"].where(upcoming["home_win_prob"] >= 0.5, 1 - upcoming["home_win_prob"])

    # Step 3: Monte Carlo over the rest of the regular season and the playoffs.
    table = standings(games).set_index("team")
    current_wins = table.loc[TEAMS, "W"].to_numpy()
    upcoming_regular = upcoming[upcoming["stage"] == "Regular Season"]
    matrix = model.matchup_matrix(trained, ratings)
    odds, season_wins = simulate.run_monte_carlo(current_wins, upcoming_regular, matrix, n_sims=n_sims, seed=seed)

    regular = games[games["stage"] == "Regular Season"]
    games_per_team = pd.concat([regular["home"], regular["away"]]).value_counts()
    odds["proj_L"] = (odds["team"].map(games_per_team).fillna(82) - odds["proj_W"]).round(1)

    return {
        "upcoming": upcoming,
        "odds": odds,
        # (n_sims x 30) final wins of every simulated season, columns in data.TEAMS order.
        # Kept for the MVP race (mvp.simulate_race), which plays the same seasons out.
        "season_wins": season_wins,
        "ratings": ratings,
        "model": trained,
        "training_games": len(training),
        "accuracy": model.backtest_accuracy(training),
    }


def expected_wins_by_date(games_table, upcoming, cutoff_date):
    """Predicted record on a future date.

    Expected wins = wins so far + the sum of win probabilities for every
    game between now and that date. (A 60% game adds 0.6 of a win.) No dice
    needed here: averages simply add up.
    """
    table = standings(games_table).set_index("team")
    before = upcoming[(upcoming["stage"] == "Regular Season") & (upcoming["date"] <= cutoff_date)]

    extra_wins = pd.Series(0.0, index=TEAMS)
    extra_games = pd.Series(0, index=TEAMS)
    for game in before.itertuples():
        extra_wins[game.home] += game.home_win_prob
        extra_wins[game.away] += 1 - game.home_win_prob
        extra_games[game.home] += 1
        extra_games[game.away] += 1

    result = pd.DataFrame({
        "conference": table["conference"],
        "W": (table["W"] + extra_wins).round(1),
        "L": (table["L"] + extra_games - extra_wins).round(1),
    })
    result["PCT"] = (result["W"] / (result["W"] + result["L"]).replace(0, 1)).round(3)
    result.index.name = "team"
    return result.sort_values("PCT", ascending=False).reset_index()
