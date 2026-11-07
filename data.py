"""Step 1: get the NBA schedule and turn it into a simple table of games.

The NBA publishes one public JSON file with every game of the current season:
preseason, regular season, NBA Cup, play-in and playoffs. Games that are over
have final scores; games that haven't happened yet just have a date and teams.

We download that file, keep a copy on disk (so the app still works offline),
and turn it into a pandas DataFrame with one row per game.
"""
import json
from pathlib import Path

import pandas as pd
import requests

SCHEDULE_URL = "https://cdn.nba.com/static/json/staticData/scheduleLeagueV2.json"
CACHE_FILE = Path(__file__).parent / "data" / "schedule.json"

# The 30 NBA teams and their conference. Preseason games against overseas
# clubs use other team codes, so we skip any game with a team not in here.
EAST = ["ATL", "BOS", "BKN", "CHA", "CHI", "CLE", "DET", "IND",
        "MIA", "MIL", "NYK", "ORL", "PHI", "TOR", "WAS"]
WEST = ["DAL", "DEN", "GSW", "HOU", "LAC", "LAL", "MEM", "MIN",
        "NOP", "OKC", "PHX", "POR", "SAC", "SAS", "UTA"]
TEAMS = EAST + WEST
CONFERENCE = {team: "East" for team in EAST} | {team: "West" for team in WEST}

# The third digit of an NBA game id tells you what kind of game it is.
# Example: 0022600123 -> "2" -> regular season.
STAGES = {
    "1": "Preseason",
    "2": "Regular Season",
    "3": "All-Star",
    "4": "Playoffs",
    "5": "Play-In",
    "6": "NBA Cup Final",
}

# gameStatus in the file: 1 = not started, 2 = in progress, 3 = final.
FINAL = 3
LIVE = 2


def download_schedule():
    """Download the schedule file and save a copy. Returns the raw JSON (a dict)."""
    response = requests.get(SCHEDULE_URL, timeout=30)
    response.raise_for_status()  # turns a failed download into an error message
    raw = response.json()
    CACHE_FILE.parent.mkdir(exist_ok=True)
    CACHE_FILE.write_text(json.dumps(raw), encoding="utf-8")  # utf-8 so Windows reads it the same way
    return raw


def load_schedule():
    """Try to download fresh data. If that fails, fall back to the saved copy."""
    try:
        return download_schedule(), "live"
    except requests.RequestException:
        if CACHE_FILE.exists():
            return json.loads(CACHE_FILE.read_text(encoding="utf-8")), "saved copy"
        raise


def parse_games(raw):
    """Turn the raw JSON into a DataFrame with one row per game."""
    schedule = raw["leagueSchedule"]
    rows = []
    for game_date in schedule["gameDates"]:
        for game in game_date["games"]:
            home = game["homeTeam"]
            away = game["awayTeam"]
            if home.get("teamTricode") not in TEAMS or away.get("teamTricode") not in TEAMS:
                continue  # skips All-Star games and overseas preseason opponents

            stage = STAGES.get(game["gameId"][2], "Other")
            if stage == "All-Star":
                continue

            rows.append({
                "game_id": game["gameId"],
                # Time in UTC for sorting; the date shown is the US Eastern date.
                "start_utc": pd.to_datetime(game.get("gameDateTimeUTC"), utc=True),
                "date": pd.to_datetime(game.get("gameDateEst", "")[:10]).date(),
                "stage": stage,
                "label": game.get("gameLabel", ""),
                "status": game["gameStatus"],
                "status_text": game.get("gameStatusText", "").strip(),
                "home": home["teamTricode"],
                "away": away["teamTricode"],
                "home_name": f'{home.get("teamCity", "")} {home.get("teamName", "")}'.strip(),
                "away_name": f'{away.get("teamCity", "")} {away.get("teamName", "")}'.strip(),
                "home_score": home.get("score") or 0,
                "away_score": away.get("score") or 0,
            })

    games = pd.DataFrame(rows).sort_values("start_utc").reset_index(drop=True)

    games["played"] = games["status"] == FINAL
    games["winner"] = None
    home_won = games["played"] & (games["home_score"] > games["away_score"])
    away_won = games["played"] & (games["away_score"] > games["home_score"])
    games.loc[home_won, "winner"] = games.loc[home_won, "home"]
    games.loc[away_won, "winner"] = games.loc[away_won, "away"]
    return games, schedule.get("seasonYear", "")


def team_names(games):
    """Map team code -> full name, e.g. 'BOS' -> 'Boston Celtics'."""
    names = dict(zip(games["home"], games["home_name"]))
    names.update(zip(games["away"], games["away_name"]))
    return names


def standings(games):
    """Current regular-season standings, built from finished games."""
    finished = games[games["played"] & (games["stage"] == "Regular Season")]
    wins = finished["winner"].value_counts()
    losers = finished["home"].where(finished["winner"] == finished["away"], finished["away"])
    losses = losers.value_counts()

    table = pd.DataFrame({"team": TEAMS})
    table["conference"] = table["team"].map(CONFERENCE)
    table["W"] = table["team"].map(wins).fillna(0).astype(int)
    table["L"] = table["team"].map(losses).fillna(0).astype(int)
    games_played = (table["W"] + table["L"]).replace(0, 1)  # avoid dividing by zero
    table["PCT"] = (table["W"] / games_played).round(3)
    return table.sort_values(["conference", "PCT", "W"], ascending=[True, False, False])


def add_games_behind(conference_table):
    """Games behind the conference leader: ((leader W - W) + (L - leader L)) / 2."""
    leader = conference_table.iloc[0]
    gb = ((leader["W"] - conference_table["W"]) + (conference_table["L"] - leader["L"])) / 2
    return conference_table.assign(GB=gb)
