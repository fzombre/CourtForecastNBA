"""Step 2: the machine-learning model that gives each game a win probability.

How it works, in plain words:

1. We walk through every finished game in date order, like replaying the season.
   Before each game we write down what we knew about both teams *at that moment*:
     - Elo rating: a single "how strong is this team" number (explained below)
     - Recent margin: average points won or lost by over the last 10 games
     - Rest: days since the team's previous game (tired teams lose more)
   Then we write down who actually won, and update the teams' numbers.

2. That gives us a table of (what we knew before the game, who won).
   A logistic regression learns from it how much each of those numbers matters.
   Logistic regression is a simple ML model that outputs a probability (0 to 1).

3. For a future game we fill in today's numbers for both teams and ask the model
   for the probability that the home team wins.

Elo in one paragraph: every team starts at 1500. After each game the winner takes
points from the loser. Beating a strong team earns more than beating a weak one,
because the win was less expected. Over time, good teams float up and bad teams
sink. Chess has used this idea since the 1960s.

Preseason games are left out: teams rest their stars, so the results say little.
"""
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

from data import TEAMS

ELO_START = 1500
ELO_K = 20            # how far ratings move after one game
ELO_HOME_EDGE = 70    # home court is worth about this many Elo points
FORM_GAMES = 10       # "recent margin" looks at this many past games
MAX_REST_DAYS = 3     # 3+ days of rest all count as "fully rested"
MIN_TRAINING_GAMES = 300  # below this (about the first 3-4 weeks), use plain Elo instead

FEATURES = ["elo_diff", "margin_diff", "rest_diff"]

# Stages whose results count when rating teams.
COUNTED_STAGES = ["Regular Season", "NBA Cup Final", "Play-In", "Playoffs"]


def elo_win_probability(elo_diff):
    """Classic Elo formula: chance that the home team wins, given (home Elo - away Elo)."""
    return 1 / (1 + 10 ** (-(elo_diff + ELO_HOME_EDGE) / 400))


def add_rest_days(games):
    """Add home_rest and away_rest: days since each team's previous game (capped)."""
    games = games.copy()
    counted = games[games["stage"].isin(COUNTED_STAGES)]

    # One row per (game, team) so we can look at each team's games in order.
    long = pd.concat([
        counted[["game_id", "date", "home"]].rename(columns={"home": "team"}),
        counted[["game_id", "date", "away"]].rename(columns={"away": "team"}),
    ])
    long["date"] = pd.to_datetime(long["date"])
    long = long.sort_values("date")
    long["rest"] = long.groupby("team")["date"].diff().dt.days
    long["rest"] = long["rest"].fillna(MAX_REST_DAYS).clip(upper=MAX_REST_DAYS)
    rest = long.set_index(["game_id", "team"])["rest"]

    games["home_rest"] = [rest.get((g, t), MAX_REST_DAYS) for g, t in zip(games["game_id"], games["home"])]
    games["away_rest"] = [rest.get((g, t), MAX_REST_DAYS) for g, t in zip(games["game_id"], games["away"])]
    return games


def replay_season(games):
    """Walk through finished games in order. Returns (training table, final team ratings).

    The training table has the features as they were *before* each game plus
    `home_win` (1 or 0). The ratings dict holds each team's Elo and recent
    margins as of today.
    """
    elo = {team: ELO_START for team in TEAMS}
    margins = {team: [] for team in TEAMS}  # list of point margins, newest last

    finished = games[games["played"] & games["stage"].isin(COUNTED_STAGES)]
    rows = []
    for game in finished.itertuples():
        # 1. Write down what we knew before tip-off.
        rows.append({
            "game_id": game.game_id,
            "elo_diff": elo[game.home] - elo[game.away],
            "margin_diff": recent_margin(margins[game.home]) - recent_margin(margins[game.away]),
            "rest_diff": game.home_rest - game.away_rest,
            "home_win": int(game.home_score > game.away_score),
        })

        # 2. Update Elo: the winner takes points from the loser.
        expected = elo_win_probability(elo[game.home] - elo[game.away])
        actual = 1 if game.home_score > game.away_score else 0
        change = ELO_K * (actual - expected)
        elo[game.home] += change
        elo[game.away] -= change

        # 3. Remember the margin for "recent form".
        margin = game.home_score - game.away_score
        margins[game.home].append(margin)
        margins[game.away].append(-margin)

    ratings = {team: {"elo": elo[team], "margin": recent_margin(margins[team])} for team in TEAMS}
    return pd.DataFrame(rows, columns=["game_id"] + FEATURES + ["home_win"]), ratings


def recent_margin(margin_list):
    """Average margin over the last FORM_GAMES games (0 if the team hasn't played)."""
    recent = margin_list[-FORM_GAMES:]
    return sum(recent) / len(recent) if recent else 0.0


def train_model(training):
    """Fit a logistic regression. Returns None if there isn't enough data yet."""
    if len(training) < MIN_TRAINING_GAMES or training["home_win"].nunique() < 2:
        return None
    model = LogisticRegression()
    model.fit(training[FEATURES], training["home_win"])
    return model


def predict(model, features):
    """Home-win probability for each row of `features` (a DataFrame with FEATURES)."""
    if model is None:
        return elo_win_probability(features["elo_diff"]).to_numpy()
    return model.predict_proba(features[FEATURES])[:, 1]


def features_for_upcoming(games, ratings):
    """Today's features for games that haven't been played yet."""
    upcoming = games[~games["played"]].copy()
    upcoming["elo_diff"] = upcoming["home"].map(lambda t: ratings[t]["elo"]) - upcoming["away"].map(lambda t: ratings[t]["elo"])
    upcoming["margin_diff"] = upcoming["home"].map(lambda t: ratings[t]["margin"]) - upcoming["away"].map(lambda t: ratings[t]["margin"])
    upcoming["rest_diff"] = upcoming["home_rest"] - upcoming["away_rest"]
    return upcoming


def matchup_matrix(model, ratings):
    """30x30 table: matrix[i][j] = chance team i beats team j when i is at home.

    The playoff simulator uses this because playoff matchups aren't on the
    schedule yet. Rest is set to equal for both teams.
    """
    rows = []
    for home in TEAMS:
        for away in TEAMS:
            rows.append({
                "elo_diff": ratings[home]["elo"] - ratings[away]["elo"],
                "margin_diff": ratings[home]["margin"] - ratings[away]["margin"],
                "rest_diff": 0,
            })
    probs = predict(model, pd.DataFrame(rows))
    return probs.reshape(len(TEAMS), len(TEAMS))


def backtest_accuracy(training):
    """How often would the model have picked the winner? Train on the first 70%
    of games, then test on the last 30% (games it has never seen)."""
    split = int(len(training) * 0.7)
    train, test = training.iloc[:split], training.iloc[split:]
    model = train_model(train)
    if model is None or len(test) == 0:
        return None
    picks = predict(model, test) > 0.5
    return {
        "model": float(np.mean(picks == test["home_win"])),
        "always_home": float(test["home_win"].mean()),
        "test_games": len(test),
    }
