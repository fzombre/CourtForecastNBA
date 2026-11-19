"""CourtForecastNBA's web API: the bridge between the Python backend and the Next.js frontend.

This file adds NO new math. It calls exactly the same functions that the Streamlit
app (app.py) calls -- load_schedule, parse_games, build_forecast, standings, ... --
and turns their results into JSON, the format a browser (and so React) understands.

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
import time

from fastapi import FastAPI, Query

from data import CONFERENCE, add_games_behind, load_schedule, parse_games, standings, team_names
from forecast import build_forecast, expected_wins_by_date

app = FastAPI(title="CourtForecastNBA API")


# ---------- Caching (the same job @st.cache_data does in app.py) ----------
# Downloading the schedule and running the Monte Carlo simulation are slow, so we keep
# the results in memory and reuse them instead of redoing the work on every request.

GAMES_TTL_SECONDS = 600  # re-download the schedule at most every 10 minutes, like app.py does
_games_cache = {"value": None, "loaded_at": 0.0}  # value = (games DataFrame, season, source)
_forecast_cache = {}  # n_sims -> the dict build_forecast() returns, for the current games


def get_games():
    """The games table, downloaded again only when the saved one is older than GAMES_TTL_SECONDS."""
    too_old = time.time() - _games_cache["loaded_at"] > GAMES_TTL_SECONDS
    if _games_cache["value"] is None or too_old:
        raw, source = load_schedule()  # live download, or the saved copy if that fails
        games, season = parse_games(raw)
        _games_cache.update(value=(games, season, source), loaded_at=time.time())
        _forecast_cache.clear()  # new games mean every old forecast is out of date
    return _games_cache["value"]


def get_forecast(n_sims):
    """build_forecast() for the current games, run once per number of simulations and then reused."""
    games, _, _ = get_games()
    if n_sims not in _forecast_cache:
        _forecast_cache[n_sims] = build_forecast(games, n_sims=n_sims, seed=42)  # seed 42 = same as app.py
    return _forecast_cache[n_sims]


def to_records(df):
    """Turn a pandas DataFrame into a list of plain dicts that JSON can hold.

    One dict per row, e.g. {"home": "BOS", "away": "NYK", "home_win_prob": 0.64, ...}.
    Going through pandas' own to_json() handles the awkward cases for us: missing values
    (NaN) become null, and numpy numbers become ordinary JSON numbers.
    """
    if "date" in df:
        df = df.assign(date=df["date"].astype(str))  # a game day as plain text: "2026-11-12"
    return json.loads(df.to_json(orient="records"))


# Only these simulation counts are allowed, the same choices as the Streamlit sidebar.
SIM_CHOICES = [500, 1000, 2000, 5000, 10000]


def check_sims(sims):
    """Fall back to the default (2000) if the frontend asks for a count we don't offer."""
    return sims if sims in SIM_CHOICES else 2000


# ---------- Endpoints: roughly one per tab of the Streamlit app ----------

@app.get("/api/overview")
def overview(sims: int = Query(2000)):
    """What the sidebar and the Model tab show: season, data source, model accuracy, Elo ratings."""
    games, season, source = get_games()
    forecast = get_forecast(check_sims(sims))
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
        "sim_choices": SIM_CHOICES,
        "team_names": names,
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
def upcoming(sims: int = Query(2000)):
    """Tab 2: every game left, with the model's pick and how sure it is (status 2 = live now)."""
    upcoming_games = get_forecast(check_sims(sims))["upcoming"]
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


@app.get("/api/projected-standings")
def projected_standings(date: dt.date, sims: int = Query(2000)):
    """Tab 4: expected records on a future date. Call it like /api/projected-standings?date=2027-01-15"""
    games, _, _ = get_games()
    upcoming_games = get_forecast(check_sims(sims))["upcoming"]
    regular_left = upcoming_games[upcoming_games["stage"] == "Regular Season"]
    projected = expected_wins_by_date(games, upcoming_games, date)
    return {
        "last_regular_season_day": regular_left["date"].max().isoformat() if len(regular_left) else None,
        "East": to_records(projected[projected["conference"] == "East"]),
        "West": to_records(projected[projected["conference"] == "West"]),
    }


@app.get("/api/odds")
def odds(sims: int = Query(2000)):
    """Tab 5: each team's chances (in %) to make the playoffs, reach each round and win the title."""
    board = get_forecast(check_sims(sims))["odds"].sort_values("champion", ascending=False)
    return to_records(board)


@app.post("/api/refresh")
def refresh():
    """The 🔄 button: forget everything cached, so the next request downloads fresh data."""
    _games_cache.update(value=None, loaded_at=0.0)
    _forecast_cache.clear()
    return {"ok": True}
