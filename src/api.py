"""CourtForecastNBA's web API: the bridge between the Python backend and the Next.js frontend.

This file adds NO new math. It calls exactly the same functions that the Streamlit
app (app.py) calls -- load_schedule, parse_games, build_forecast, standings, ... --
and turns their results into JSON, the format a browser (and so React) understands.
The one addition is the MVP race (/api/mvp), which only the website has: it calls
players.py and mvp.py, which the Streamlit app doesn't use.

    Python backend (data.py, model.py, simulate.py, forecast.py)   <- unchanged
          |
       api.py   (this file: FastAPI turns Python results into JSON over HTTP)
          |
    Next.js frontend in web/   (TypeScript + React: draws the tables and charts)

Run it from the project folder with:
    py -m uvicorn api:app --app-dir src --reload --port 8000
Then open http://127.0.0.1:8000/docs: FastAPI builds a page there where you can try
every endpoint by hand and see the exact JSON the frontend will receive.
"""
import datetime as dt
import json
import threading
import time

from fastapi import FastAPI
from nba_api.stats.static import teams as nba_teams

import mvp
from data import CONFERENCE, add_games_behind, load_schedule, parse_games, standings, team_names
from forecast import build_forecast, expected_wins_by_date
from players import load_player_stats, parse_player_stats

app = FastAPI(title="CourtForecastNBA API")

# Each team's official NBA id, e.g. "BOS" -> 1610612738. The frontend needs it to build the
# address of the team's logo on NBA.com. nba_api ships this list inside the library, so it
# works offline and never calls stats.nba.com. (They're the same ids as "teamId" in the schedule.)
TEAM_IDS = {team["abbreviation"]: team["id"] for team in nba_teams.get_teams()}


# ---------- Caching (the same job @st.cache_data does in app.py) ----------
# Downloading the schedule and running the Monte Carlo simulation are slow, so we keep
# the results in memory and reuse them instead of redoing the work on every request.

GAMES_TTL_SECONDS = 600  # re-download the schedule at most every 10 minutes, like app.py does
_games_cache = {"value": None, "loaded_at": 0.0}  # value = (games DataFrame, season, source)
_forecast_cache = {}  # "forecast" -> the dict build_forecast() returns, for the current games

# The MVP tab's caches (see get_players and get_mvp_race below).
PLAYERS_TTL_SECONDS = 600  # player stats change as games finish, like the schedule: same 10 minutes
_players_cache = {"value": None, "loaded_at": 0.0}  # value = (players DataFrame, source)
# The MVP race depends on both the schedule (through the simulated seasons) and the player
# stats, so it remembers which download of each it was computed from ("key"), and is
# computed again as soon as either one is newer.
_mvp_cache = {"key": None, "value": None}
# The trained MVP model and its backtest. They only depend on data/mvp_history.csv, which
# never changes while the app runs, so they're computed once and kept until the app stops.
_mvp_model_cache = {}

# How many seasons the Monte Carlo simulation plays out. The app picks this, not the
# person using the website: it's a quality setting for the predictions, not a choice.
# More simulations give steadier odds, but take longer:
#   2,000 seasons:  about 0.5 s, but the title favorite can change from run to run
#  10,000 seasons:  about 2 s, title odds steady to within about half a percent
#  20,000 seasons:  about 5 s, barely steadier than 10,000
# The result is cached (see get_forecast), so this cost is paid at most once per download.
N_SIMS = 10_000

# The website asks for several things at once when a page opens (the header and the tab
# both need the forecast). FastAPI answers those requests in parallel threads, so without
# this lock two threads could each start the same slow download or simulation. With it,
# the second thread waits for the first and then reuses its result from the cache.
# It's an RLock ("re-entrant") because get_forecast() calls get_games() while holding it.
_cache_lock = threading.RLock()


def get_games():
    """The games table, downloaded again only when the saved one is older than GAMES_TTL_SECONDS."""
    with _cache_lock:
        too_old = time.time() - _games_cache["loaded_at"] > GAMES_TTL_SECONDS
        if _games_cache["value"] is None or too_old:
            raw, source = load_schedule()  # live download, or the saved copy if that fails
            games, season = parse_games(raw)
            _games_cache.update(value=(games, season, source), loaded_at=time.time())
            _forecast_cache.clear()  # new games mean every old forecast is out of date
        return _games_cache["value"]


def get_forecast():
    """build_forecast() for the current games: run once with N_SIMS seasons, then reused."""
    with _cache_lock:
        games, _, _ = get_games()
        if "forecast" not in _forecast_cache:
            # seed=42 makes the dice rolls repeatable, so the same games always give the same odds.
            _forecast_cache["forecast"] = build_forecast(games, n_sims=N_SIMS, seed=42)
        return _forecast_cache["forecast"]


def get_players():
    """This season's player stats, downloaded again only when older than PLAYERS_TTL_SECONDS."""
    with _cache_lock:
        too_old = time.time() - _players_cache["loaded_at"] > PLAYERS_TTL_SECONDS
        if _players_cache["value"] is None or too_old:
            raw, source = load_player_stats()  # live download, or the saved copy if that fails
            _players_cache.update(value=(parse_player_stats(raw), source), loaded_at=time.time())
        return _players_cache["value"]


def get_mvp_model():
    """The MVP model trained on every past season, plus its backtest. Computed once per run."""
    with _cache_lock:
        if not _mvp_model_cache:
            history = mvp.load_history()
            _mvp_model_cache.update(history=history, model=mvp.train(history), backtest=mvp.backtest(history))
        return _mvp_model_cache


def get_mvp_race():
    """mvp.mvp_race() for the current schedule and player stats, reused until either changes."""
    with _cache_lock:
        games, _, _ = get_games()
        players, _ = get_players()
        forecast = get_forecast()  # the simulated seasons the race plays out
        key = (_games_cache["loaded_at"], _players_cache["loaded_at"])
        if _mvp_cache["key"] != key:
            trained = get_mvp_model()
            race = mvp.mvp_race(trained["model"], players, games, forecast["season_wins"],
                                history=trained["history"], seed=42)  # seed: same data, same odds
            _mvp_cache.update(key=key, value=race)
        return _mvp_cache["value"]


def to_records(df):
    """Turn a pandas DataFrame into a list of plain dicts that JSON can hold.

    One dict per row, e.g. {"home": "BOS", "away": "NYK", "home_win_prob": 0.64, ...}.
    Going through pandas' own to_json() handles the awkward cases for us: missing values
    (NaN) become null, and numpy numbers become ordinary JSON numbers.
    """
    if "date" in df:
        df = df.assign(date=df["date"].astype(str))  # a game day as plain text: "2026-11-12"
    return json.loads(df.to_json(orient="records"))


# ---------- Endpoints: roughly one per tab of the Streamlit app ----------

@app.get("/api/overview")
def overview():
    """What the sidebar and the Model tab show: season, data source, model accuracy, Elo ratings."""
    games, season, source = get_games()
    forecast = get_forecast()
    names = team_names(games)
    trained = forecast["model"]  # None early in the season, when the app uses plain Elo
    ratings = [
        {"team": team, "name": names.get(team, team), "conference": CONFERENCE[team],
         "elo": round(r["elo"], 1), "margin": round(r["margin"], 1)}
        for team, r in forecast["ratings"].items()
    ]
    return {
        "season": season,
        "source": source,
        "n_sims": N_SIMS,  # how many seasons the odds are based on, for the Playoff odds caption
        "team_names": names,
        "team_ids": TEAM_IDS,  # "BOS" -> 1610612738, used by the frontend to show each team's logo
        "training_games": forecast["training_games"],
        "using_model": trained is not None,
        # Weights in the same order as model.FEATURES: Elo gap, recent margin gap, rest days gap.
        "weights": [round(float(w), 4) for w in trained.coef_[0]] if trained is not None else None,
        "accuracy": forecast["accuracy"],  # None when there aren't enough finished games yet
        "ratings": sorted(ratings, key=lambda r: r["elo"], reverse=True),
    }


@app.get("/api/results")
def results():
    """Tab 1: every finished game, newest first."""
    games, _, _ = get_games()
    played = games[games["played"]].sort_values("start_utc", ascending=False)
    return to_records(played[["game_id", "date", "stage", "away", "away_name", "away_score",
                              "home", "home_name", "home_score", "winner"]])


@app.get("/api/upcoming")
def upcoming():
    """Tab 2: every game left, with the model's pick and how sure it is (status 2 = live now)."""
    upcoming_games = get_forecast()["upcoming"]
    return to_records(upcoming_games[["game_id", "date", "stage", "status", "status_text",
                                      "away", "away_name", "away_score", "home", "home_name", "home_score",
                                      "home_win_prob", "predicted_winner", "confidence"]])


@app.get("/api/standings")
def current_standings():
    """Tab 3: live East and West standings, each with games behind the conference leader."""
    games, _, _ = get_games()
    table = standings(games)
    return {conference: to_records(add_games_behind(table[table["conference"] == conference]))
            for conference in ["East", "West"]}


def projection_dates(regular_left):
    """The dates you can pick on the Predicted standings tab, exactly like the Streamlit slider:
    one a week starting a week from today, plus the last day of the regular season."""
    today = dt.date.today()
    last_day = regular_left["date"].max()
    weeks = [today + dt.timedelta(days=d) for d in range(7, (last_day - today).days, 7)]
    return weeks + [last_day]


@app.get("/api/projected-standings")
def projected_standings(date: dt.date | None = None):
    """Tab 4: expected records on a future date.

    /api/projected-standings                  -> the first date you can pick (a week from today)
    /api/projected-standings?date=2027-01-15  -> that date
    The answer also lists every date you can pick ("date_options"), so the frontend can build
    its date picker without repeating this logic. date is null once the regular season is over.
    """
    games, _, _ = get_games()
    upcoming_games = get_forecast()["upcoming"]
    regular_left = upcoming_games[upcoming_games["stage"] == "Regular Season"]
    if len(regular_left) == 0:  # regular season over: the current standings are final
        return {"date": None, "date_options": [], "East": [], "West": []}

    options = projection_dates(regular_left)
    chosen = date or options[0]
    projected = expected_wins_by_date(games, upcoming_games, chosen)
    return {
        "date": chosen.isoformat(),  # "2027-01-15"
        "date_options": [day.isoformat() for day in options],
        "East": to_records(projected[projected["conference"] == "East"]),
        "West": to_records(projected[projected["conference"] == "West"]),
    }


@app.get("/api/odds")
def odds():
    """Tab 5: each team's chances (in %) to make the playoffs, reach each round and win the title."""
    board = get_forecast()["odds"].sort_values("champion", ascending=False)
    return to_records(board)


# How many candidates /api/mvp sends: everyone in the top MVP_LADDER_SIZE of the ladder,
# plus anyone else with at least MVP_MIN_CHANCE percent to win, at most MVP_MAX_ROWS in all.
# (There are ~150 candidates; most have a chance of 0.0001%, which isn't worth a row.)
MVP_LADDER_SIZE = 15
MVP_MIN_CHANCE = 0.05
MVP_MAX_ROWS = 25


@app.get("/api/mvp")
def mvp_race():
    """The MVP tab (web only, after Playoff odds): today's ladder and each candidate's chance to win.

    "candidates" is sorted by chance to win, best first. Each one has:
      - his stats so far (gp, pts, reb, ast, ts_pct, plus_minus, w, l, ...);
      - rank / today: his place on the ladder "if the season ended today" and the model's
        chance for him on today's stats (rank is null if he isn't on track for the games rule);
      - chance: his chance to win MVP at the end of the season, in percent;
      - eligible / proj_gp: % of simulated seasons in which he reaches the required games,
        and the games he's expected to finish with.
    "backtest" says how often the model picked the real MVP in past seasons it never saw,
    and "weights" how much each stat matters (per standard deviation, see mvp.fit_softmax).
    """
    _, season, _ = get_games()
    _, source = get_players()
    trained = get_mvp_model()
    race = get_mvp_race()

    shown = race[(race["rank"] <= MVP_LADDER_SIZE) | (race["chance"] >= MVP_MIN_CHANCE)].head(MVP_MAX_ROWS)
    columns = ["player_id", "name", "team", "gp", "team_gp", "required", "can_miss", "min",
               "pts", "reb", "ast", "ts_pct", "plus_minus", "w", "l", "win_pct",
               "rank", "today", "chance", "eligible", "proj_gp"]
    shown = shown[columns].round({"today": 2, "chance": 2, "eligible": 1, "proj_gp": 1, "win_pct": 3, "ts_pct": 3})
    return {
        "season": season,
        "source": source,              # where the player stats came from: "live (nba_api)" or "saved copy (...)"
        "n_sims": N_SIMS,
        "games_required": mvp.GAMES_REQUIRED,
        "season_games": mvp.SEASON_GAMES,
        "backtest": trained["backtest"],
        "weights": [{"feature": feature, "weight": round(float(weight), 3)}
                    for feature, weight in zip(mvp.FEATURES, trained["model"]["weights"])],
        "candidates": to_records(shown),  # NaN rank (not on the ladder) becomes null
    }


@app.post("/api/refresh")
def refresh():
    """The 🔄 button: forget everything cached, so the next request downloads fresh data."""
    _games_cache.update(value=None, loaded_at=0.0)
    _forecast_cache.clear()
    _players_cache.update(value=None, loaded_at=0.0)
    _mvp_cache.update(key=None, value=None)
    # (_mvp_model_cache stays: it only depends on the history file, which a refresh doesn't change.)
    return {"ok": True}
