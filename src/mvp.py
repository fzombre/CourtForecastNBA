"""The MVP race: who would win MVP if the season ended today, and who is likely to win it.

There is no official MVP ranking during the season (NBA.com's "MVP Ladder" is a column
written by a reporter, not data). So we build our own, in two steps.

Step 1: a model of how voters pick, learned from 30 past seasons
------------------------------------------------------------------
data/mvp_history.csv (made by scripts/build_mvp_history.py) holds every regular's
per-game stats from 1996-97 to last season, and which one of them actually won MVP.

The model gives every candidate a *score*: a weighted sum of six numbers.

    score = w1*points + w2*rebounds + w3*assists + w4*true shooting % + w5*plus/minus + w6*team win %

and turns the scores of one season's candidates into chances that add up to 100%:

    chance(player) = e^score(player) / (sum of e^score over every candidate that season)

This is called a *softmax* (or "conditional logit"). It's the same idea as the
logistic regression in model.py, stretched from two options (home or away wins) to a
whole field of candidates: a higher score means a bigger slice, and the slices always
add up to exactly one winner. Training finds the weights that gave the real MVPs the
biggest slices of their seasons (see fit_softmax).

Step 2: play out the rest of the season (Monte Carlo, like simulate.py)
-----------------------------------------------------------------------
"If the season ended today" is the *ladder*: today's stats through the model.
But the season isn't over. For the *prediction*, we take the 10,000 simulated seasons
that simulate.py already plays for the playoff odds, and in each one we also play out
every candidate's rest of the season:
  - how many more games he plays (stars miss games; see availability below),
  - whether he reaches the 65 games the NBA requires for MVP (the rule since 2023-24),
  - his team's final record (straight from that simulated season),
  - how his averages drift as more games are played (small early in the year, as the
    sample is small; nothing at the end, when the numbers are final).
Then we run the model on each simulated final stat line, and average the chances over
all simulated seasons. A player who wins 30% of the slices on average has a 30% chance.
"""
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from data import TEAMS

HISTORY_FILE = Path(__file__).resolve().parent.parent / "data" / "mvp_history.csv"

# Every MVP since 1996-97 (the first season stats.nba.com has plus/minus for). The build
# script uses this list to mark the winner in each season of mvp_history.csv. Written
# without accents; the script matches names with accents removed ("Jokić" = "Jokic").
# Once a year, after the award is announced: add the new winner here and re-run
# scripts/build_mvp_history.py.
MVP_WINNERS = {
    "1996-97": "Karl Malone",
    "1997-98": "Michael Jordan",
    "1998-99": "Karl Malone",
    "1999-00": "Shaquille O'Neal",
    "2000-01": "Allen Iverson",
    "2001-02": "Tim Duncan",
    "2002-03": "Tim Duncan",
    "2003-04": "Kevin Garnett",
    "2004-05": "Steve Nash",
    "2005-06": "Steve Nash",
    "2006-07": "Dirk Nowitzki",
    "2007-08": "Kobe Bryant",
    "2008-09": "LeBron James",
    "2009-10": "LeBron James",
    "2010-11": "Derrick Rose",
    "2011-12": "LeBron James",
    "2012-13": "LeBron James",
    "2013-14": "Kevin Durant",
    "2014-15": "Stephen Curry",
    "2015-16": "Stephen Curry",
    "2016-17": "Russell Westbrook",
    "2017-18": "James Harden",
    "2018-19": "Giannis Antetokounmpo",
    "2019-20": "Giannis Antetokounmpo",
    "2020-21": "Nikola Jokic",
    "2021-22": "Nikola Jokic",
    "2022-23": "Joel Embiid",
    "2023-24": "Nikola Jokic",
    "2024-25": "Shai Gilgeous-Alexander",
    "2025-26": "Shai Gilgeous-Alexander",
}

# The six numbers the model looks at (column names from players.py). We tried others
# (steals + blocks, turnovers, dropping true shooting); these six predicted past MVPs
# best when each season was hidden from training in turn (see backtest).
FEATURES = ["pts", "reb", "ast", "ts_pct", "plus_minus", "win_pct"]

# Who counts as a candidate. Nobody in our 30 seasons won MVP playing under 25 minutes
# a game, or missing more than 40% of his team's games, so the model only compares
# players who pass both. (Leaving in hundreds of bench players wouldn't change the
# chances, it would just make every calculation slower.)
MIN_MINUTES = 25.0
MIN_GAMES_SHARE = 0.6

# The NBA's games-played rule (since 2023-24): to win MVP you must play 65 of the 82
# games. For a season of a different length (a lockout, or the tests' made-up schedule)
# we scale it: 65/82 of the season, about 79%.
GAMES_REQUIRED = 65
SEASON_GAMES = 82

# How strongly training pulls the weights toward zero ("L2 regularization"). Thirty
# winners is not a lot of examples; a small pull stops the model from leaning too hard
# on one odd season. 0.5 did best in the backtest (0.05 and 2 were both a bit worse).
L2_PENALTY = 0.5

# --- For the Monte Carlo (Step 2) ---

# How far a player's season averages can still drift while there are games left to play.
# Each number is a per-game standard deviation in that stat's own units, and
# simulate_race() shrinks it as the season goes on (see the `spread` formula there).
#
# They're *measured*, not guessed: scripts/check_mvp_drift.py downloads every player's
# averages as of November 20 in the last five seasons and compares them with how those
# players actually finished. We started from typical game-to-game swings (a 30-point
# scorer has nights of 22 and nights of 38: about 7 points) and scaled each one up until
# the simulated drift matched the real drift. Real averages move more than game-to-game
# luck alone explains (roles change, players get hurt or traded, teams change pace).
DRIFT_SD = {"pts": 10.9, "reb": 3.3, "ast": 3.5, "ts_pct": 0.15, "plus_minus": 13.5}

# Hot starts cool off. After 15 games a player scoring 38 a night is very good, but
# he's more likely to finish at 34 than at 38: some of those 15 games were lucky. So we
# estimate his *true* level by blending this season with last season's averages (from
# mvp_history.csv), counting last season as if it were PRIOR_SEASON_GAMES games of this
# one. In November that blend leans on last season; by March this season's 60 games
# outweigh it. A player with no row last season (a rookie, or a player who was hurt)
# is blended with the average candidate instead, which pulls a hot rookie back further.
# (This is the standard "regression to the mean" trick, the same reason the first weeks
# of Elo in model.py are close to coin flips.)
PRIOR_SEASON_GAMES = 15

# Availability: how many of his team's remaining games a candidate plays.
#
# His expected share of games blends what he has done so far this season (games played /
# his team's games) with last season's share, counted as if it were PRIOR_GAMES extra
# games. A player with no row last season gets PRIOR_AVAILABILITY: across our 30 seasons,
# players averaging 30+ minutes played 85.5% of their team's games (about 70 of 82).
# The blend stops a player who sat out 1 of his team's first 3 games being treated as a
# 67% player.
PRIOR_AVAILABILITY = 0.85
PRIOR_GAMES = 10

# Injuries don't strike one game at a time: one sprained ankle costs 15 games in a row,
# and some seasons a star plays all 82. So in each simulated season we first draw that
# season's availability rate for him (from a "Beta distribution" around his expected
# share), then the games he plays at that rate. AVAILABILITY_SPREAD sets how widely the
# rate varies: smaller = wider. Measured across 30 seasons, the share of games played by
# 30-minute players varies like a spread of about 4.6. Part of that variety is between
# players (some are just more durable), which the blend above already covers, so we use
# a slightly tighter 6. Without this, the model said a healthy star had a 99% chance to
# reach 65 games in November; in reality stars miss the cut-off most seasons.
AVAILABILITY_SPREAD = 6.0


def load_history(path=HISTORY_FILE):
    """The 30 past seasons, one row per regular per season (see build_mvp_history.py)."""
    return pd.read_csv(path, encoding="utf-8")


def training_pool(history):
    """The candidates of every past season: enough minutes and enough games.

    "Enough games" is a share of that season's length. The season length is the most
    games anyone played that year: 82 in a normal year, 50 in the 1998-99 lockout.
    """
    season_length = history.groupby("season")["gp"].transform("max")
    keep = (history["min"] >= MIN_MINUTES) & (history["gp"] >= MIN_GAMES_SHARE * season_length)
    return history[keep].reset_index(drop=True)


# ---------- The softmax model ----------

def softmax_by_group(scores, groups):
    """Turn scores into chances that add up to 1 inside each group (season, or simulation).

    scores: array of numbers, one per candidate
    groups: array of the same length saying which group each candidate is in (0, 1, 2, ...)

    The "subtract the group's biggest score first" step doesn't change the answer
    (it cancels out above and below the fraction) but stops e^score from overflowing.
    """
    n_groups = groups.max() + 1
    biggest = np.full(n_groups, -np.inf)
    np.maximum.at(biggest, groups, scores)       # the biggest score in each group
    exp = np.exp(scores - biggest[groups])
    totals = np.bincount(groups, weights=exp, minlength=n_groups)
    return exp / totals[groups]


def fit_softmax(pool, l2=L2_PENALTY):
    """Learn the six weights from past seasons. Returns the model as a plain dict.

    First every feature is *standardized*: turned into "how many standard deviations
    above the average candidate" (z = (x - mean) / sd). Points per game (around 25) and
    true shooting (around 0.57) live on very different scales; standardizing puts them
    on one scale, so the weights can be compared with each other and the L2 pull treats
    them all alike.

    Then we look for the weights that make the real winners' chances as high as
    possible. Precisely: we minimize the "negative log-likelihood", minus the sum over
    seasons of log(chance the model gave that season's real MVP), plus the L2 pull.
    scipy's BFGS method does the searching; we hand it the gradient (the direction the
    error grows fastest) so it knows which way to step.
    """
    X = pool[FEATURES].to_numpy(dtype=float)
    mean, std = X.mean(axis=0), X.std(axis=0)
    Z = (X - mean) / std
    groups = pd.factorize(pool["season"])[0]   # "1996-97" -> 0, "1997-98" -> 1, ...
    won = pool["mvp"].to_numpy() == 1

    def loss_and_gradient(weights):
        scores = Z @ weights
        chances = softmax_by_group(scores, groups)
        loss = -np.log(chances[won]).sum() + l2 * weights @ weights
        # The gradient of a softmax log-likelihood has a neat form: for each season,
        # (the winner's features) - (the chance-weighted average candidate's features).
        gradient = -(Z[won].sum(axis=0) - (chances[:, None] * Z).sum(axis=0)) + 2 * l2 * weights
        return loss, gradient

    result = minimize(loss_and_gradient, np.zeros(len(FEATURES)), jac=True, method="BFGS")
    return {"weights": result.x, "mean": mean, "std": std}


def score(model, features):
    """Each row's model score. `features` is a DataFrame or an array with the FEATURES columns
    in order (raw units: points, rebounds, ...). Standardized with the training mean and sd."""
    X = features[FEATURES].to_numpy(dtype=float) if isinstance(features, pd.DataFrame) else features
    return ((X - model["mean"]) / model["std"]) @ model["weights"]


def train(history=None):
    """The model trained on every past season. (What the app uses.)"""
    history = load_history() if history is None else history
    return fit_softmax(training_pool(history))


def backtest(history=None):
    """How good is the model? Hide one season, train on the other 29, see whom it picks.

    Doing that for each of the 30 seasons in turn ("leave one season out") means every
    season is judged by a model that never saw it, the same idea as the train/test split
    in model.backtest_accuracy. Returns how often the real MVP was the model's #1 pick,
    and how often he was in its top 3.
    """
    history = load_history() if history is None else history
    pool = training_pool(history)
    seasons = list(pool["season"].unique())
    top1 = top3 = 0
    for season in seasons:
        model = fit_softmax(pool[pool["season"] != season])
        this_season = pool[pool["season"] == season]
        order = np.argsort(-score(model, this_season))        # best score first
        winners_in_order = this_season["mvp"].to_numpy()[order]
        top1 += int(winners_in_order[0])
        top3 += int(winners_in_order[:3].sum())
    return {"seasons": len(seasons), "top1": top1, "top3": top3,
            "first_season": seasons[0], "last_season": seasons[-1]}


# ---------- This season ----------

def team_games(games):
    """Per team: regular-season games played so far, games left, and wins so far.

    Returns a DataFrame indexed by team code with these columns:
      total            games in the team's whole regular season
      played           games finished so far
      left             total - played (what a player can still play)
      scheduled_left   games left that are already on the schedule (what simulate.py played)
      wins             wins so far

    Why "total" and "scheduled" can differ: until the NBA Cup group stage ends in early
    December, NBA.com's schedule lists only 80 games per team. The last 2 are added once
    the Cup's knockout round is known. So when the schedule looks like a real NBA season
    (at least 90% of 82 games for some team), we count the season as 82 games. A shorter
    made-up schedule, like the one in the tests, is taken as it is.
    """
    regular = games[games["stage"] == "Regular Season"]
    scheduled = pd.concat([regular["home"], regular["away"]]).value_counts()
    finished = regular[regular["played"]]
    played = pd.concat([finished["home"], finished["away"]]).value_counts()
    wins = finished["winner"].value_counts()

    table = pd.DataFrame(index=pd.Index(TEAMS, name="team"))
    table["scheduled"] = table.index.map(scheduled).fillna(0).astype(int)
    table["played"] = table.index.map(played).fillna(0).astype(int)
    table["wins"] = table.index.map(wins).fillna(0).astype(int)
    looks_like_nba_season = table["scheduled"].max() >= 0.9 * SEASON_GAMES
    table["total"] = table["scheduled"].clip(lower=SEASON_GAMES) if looks_like_nba_season else table["scheduled"]
    table["left"] = table["total"] - table["played"]
    table["scheduled_left"] = table["scheduled"] - table["played"]
    return table


def last_season_availability(players, history):
    """Each player's share of his team's games played last season (newest season in the
    history file); PRIOR_AVAILABILITY for players with no row there. Same row order as `players`.

    The season's length is the most games anyone played that year, like training_pool().
    """
    last = history[history["season"] == history["season"].max()]
    share = (last["gp"] / last["gp"].max()).clip(upper=1.0)
    by_player = pd.Series(share.to_numpy(), index=last["player_id"]).groupby(level=0).max()
    return players["player_id"].map(by_player).fillna(PRIOR_AVAILABILITY).reset_index(drop=True)


def true_level(players, history):
    """Each player's estimated *true* per-game level in every stat that drifts (see PRIOR_SEASON_GAMES).

    true level = (games this season x this season's average + PRIOR_SEASON_GAMES x last season's)
                 / (games this season + PRIOR_SEASON_GAMES)

    "Last season" is the newest season in mvp_history.csv. Players without a row there
    get the average candidate of that season instead. Returns a DataFrame with one column
    per stat in DRIFT_SD, in the same row order as `players`.
    """
    stats = list(DRIFT_SD)
    last = history[history["season"] == history["season"].max()]
    last_pool = training_pool(last)
    last_by_player = last.drop_duplicates("player_id").set_index("player_id")[stats]

    prior = last_by_player.reindex(players["player_id"]).reset_index(drop=True)
    prior = prior.fillna(last_pool[stats].mean())   # no row last season -> the average candidate

    gp = players["gp"].to_numpy(dtype=float)[:, None]
    now = players[stats].to_numpy(dtype=float)
    blended = (gp * now + PRIOR_SEASON_GAMES * prior.to_numpy()) / (gp + PRIOR_SEASON_GAMES)
    return pd.DataFrame(blended, columns=stats, index=players.index)


def candidates(players, teams):
    """This season's MVP candidates, with the games-played rule worked out for each.

    players: players.parse_player_stats() output
    teams:   team_games() output

    Added columns:
      team_gp        his team's games so far (the most he could have played)
      required       games he must reach to be eligible (65 in an 82-game season)
      can_miss       games he can still miss and stay eligible (negative = ruled out)
      qualifies_now  on track today: played at least the required share of games so far
                     (used for the "if the season ended today" ladder)
    """
    pool = players[players["team"].isin(TEAMS) & (players["min"] >= MIN_MINUTES)].copy()
    pool["team_gp"] = pool["team"].map(teams["played"]).astype(int)
    pool["team_total"] = pool["team"].map(teams["total"]).astype(int)
    # A player traded mid-season can have more games than his new team; cap at his team's.
    pool["team_gp"] = np.maximum(pool["team_gp"], pool["gp"])
    pool["required"] = np.round(GAMES_REQUIRED / SEASON_GAMES * pool["team_total"]).astype(int)
    pool["can_miss"] = (pool["team_total"] - pool["required"]) - (pool["team_gp"] - pool["gp"])
    pool["qualifies_now"] = (pool["gp"] >= GAMES_REQUIRED / SEASON_GAMES * pool["team_gp"]) & (pool["can_miss"] >= 0)
    # Players who can no longer reach the required games have no chance; drop them.
    return pool[pool["can_miss"] >= 0].reset_index(drop=True)


def ladder(model, pool):
    """"If the season ended today": the model's chances using today's stats as they are.

    Only players on track for the games rule are ranked. Returns a copy of the pool with
    `today` (percent, the whole ladder adds up to 100) and `rank` (1 = top; NaN if not ranked).
    """
    pool = pool.copy()
    pool["today"] = 0.0
    on_track = pool["qualifies_now"].to_numpy()
    if on_track.any():
        chances = softmax_by_group(score(model, pool[on_track]), np.zeros(on_track.sum(), dtype=int))
        pool.loc[on_track, "today"] = chances * 100
    pool["rank"] = pool["today"].where(on_track).rank(ascending=False, method="first")
    return pool


def simulate_race(model, pool, teams, season_wins, history, seed=None):
    """Step 2: each candidate's chance to win MVP, over the simulated seasons.

    season_wins: (n_sims x 30) array of final regular-season wins, one row per simulated
                 season (forecast.build_forecast()["season_wins"], columns in TEAMS order)
    history:     mvp_history.csv, for last season's averages (see true_level)

    Adds to a copy of the pool:
      chance      percent chance to win MVP (all candidates add up to ~100)
      eligible    percent of simulations in which he reaches the required games
      proj_gp     games played at the end of the season, on average
    Every array below is (candidates x simulations): one row per player, one column
    per simulated season.
    """
    rng = np.random.default_rng(seed)
    pool = pool.copy()
    n_sims = season_wins.shape[0]
    team_column = pool["team"].map({team: i for i, team in enumerate(TEAMS)}).to_numpy()

    gp = pool["gp"].to_numpy(dtype=float)[:, None]
    left = pool["team"].map(teams["left"]).to_numpy()

    # How many of his team's remaining games he plays, in each simulated season.
    # 1) His expected share: this season so far, blended with last season (see PRIOR_GAMES).
    prior_share = last_season_availability(pool, history).to_numpy()
    expected = (pool["gp"].to_numpy() + PRIOR_GAMES * prior_share) / (pool["team_gp"].to_numpy() + PRIOR_GAMES)
    expected = np.clip(expected, 0.02, 0.98)  # the Beta draw below needs a value strictly between 0 and 1
    # 2) This simulated season's rate: a Beta draw around that share (see AVAILABILITY_SPREAD).
    a = (AVAILABILITY_SPREAD * expected)[:, None]
    b = (AVAILABILITY_SPREAD * (1 - expected))[:, None]
    rate = rng.beta(a, b, size=(len(pool), n_sims))
    # 3) The games he plays at that rate.
    more_games = rng.binomial(left[:, None], rate)
    final_gp = gp + more_games
    eligible = final_gp >= pool["required"].to_numpy()[:, None]

    # His team's win rate over its remaining games in each simulated season: the team's
    # simulated final wins minus its wins so far, divided by the games simulate.py played
    # (the ones already on the schedule; see team_games for the 2 that aren't yet).
    team_wins_now = pool["team"].map(teams["wins"]).to_numpy()[:, None]
    team_rest_wins = season_wins[:, team_column].T - team_wins_now
    scheduled_left = pool["team"].map(teams["scheduled_left"]).to_numpy()
    rest_win_rate = team_rest_wins / np.maximum(scheduled_left, 1)[:, None]
    # His final record = his record so far + (the games he plays from now on) x (that rate).
    final_win_pct = (pool["w"].to_numpy()[:, None] + rest_win_rate * more_games) / final_gp

    # His final averages = (today's games x today's average + remaining games x the
    # average he posts in them) / all his games. The average over the remaining games is
    # random, centered on his *true level* (see true_level: today blended with last
    # season, so hot starts cool off). Its spread has two parts:
    #   - we only know his true level from gp + PRIOR_SEASON_GAMES games' worth of evidence,
    #   - the remaining games themselves are random (a hot or cold month).
    # Both shrink as the season goes on, and at the very end there's nothing left to drift.
    final = {"win_pct": final_win_pct}
    level = true_level(pool, history)
    rest_share = more_games / final_gp
    spread = np.sqrt(1 / (gp + PRIOR_SEASON_GAMES) + 1 / np.maximum(more_games, 1))
    for feature, drift_sd in DRIFT_SD.items():
        now = pool[feature].to_numpy(dtype=float)[:, None]
        rest_average = level[feature].to_numpy()[:, None] + rng.standard_normal((len(pool), n_sims)) * drift_sd * spread
        final[feature] = (1 - rest_share) * now + rest_share * rest_average

    # Model score of every simulated final stat line (the same formula as score()).
    scores = np.zeros((len(pool), n_sims))
    for i, feature in enumerate(FEATURES):
        scores += model["weights"][i] * (final[feature] - model["mean"][i]) / model["std"][i]
    scores[~eligible] = -np.inf   # under the games rule: can't win in that simulated season

    # Softmax down each column (each simulated season). A season where nobody is eligible
    # (possible only with tiny made-up data) gives nobody a slice instead of dividing by zero.
    best = scores.max(axis=0)
    anyone = np.isfinite(best)
    exp = np.where(eligible, np.exp(scores - np.where(anyone, best, 0)), 0.0)
    totals = exp.sum(axis=0)
    chances = np.divide(exp, totals, out=np.zeros_like(exp), where=totals > 0)

    pool["chance"] = chances.mean(axis=1) * 100
    pool["eligible"] = eligible.mean(axis=1) * 100
    pool["proj_gp"] = final_gp.mean(axis=1)
    return pool


def mvp_race(model, players, games, season_wins, history=None, seed=None):
    """Everything the MVP tab shows, in one table: one row per candidate, best chance first."""
    history = load_history() if history is None else history
    teams = team_games(games)
    pool = candidates(players, teams)
    if pool.empty:  # before the first game of the season
        return pool.assign(today=[], rank=[], chance=[], eligible=[], proj_gp=[])
    race = simulate_race(model, ladder(model, pool), teams, season_wins, history, seed=seed)
    return race.sort_values(["chance", "today"], ascending=False).reset_index(drop=True)
