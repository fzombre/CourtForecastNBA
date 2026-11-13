"""Step 1: get the NBA schedule and turn it into a simple table of games.

We get the schedule with the free nba_api library (https://github.com/swar/nba_api).
Its "scheduleleaguev2" endpoint returns every game of the season: preseason,
regular season, NBA Cup, play-in and playoffs. Games that are over have final
scores; games that haven't happened yet just have a date and teams. No API key.
NBA.com updates it as games finish, so the standings we build from it stay live.

We keep a copy on disk (so the app still works offline), and turn it into a
pandas DataFrame with one row per game.
"""
import datetime as dt
import json
from pathlib import Path

import pandas as pd
from nba_api.stats.library.http import NBAStatsHTTP  # the part of nba_api that talks to stats.nba.com

CACHE_FILE = Path(__file__).resolve().parent.parent / "data" / "schedule.json"  # <project>/data/, next to src/
TIMEOUT = 30  # seconds to wait for NBA.com before giving up (so the app never hangs forever)

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


def current_season(today=None):
    """The NBA season as nba_api writes it, e.g. '2026-27'. """
    today = today or dt.date.today()
    first_year = today.year if today.month >= 7 else today.year - 1
    return f"{first_year}-{(first_year + 1) % 100:02d}"   # 2026 -> "2026-27"


def download_schedule(season=None):
    """Ask stats.nba.com for this season's schedule. Returns the raw JSON (a dict)
    and saves a copy to disk. The JSON looks like:
        {"leagueSchedule": {"seasonYear": "2026-27", "gameDates": [{"games": [...]}, ...]}}
    """
    response = NBAStatsHTTP().send_api_request(
        endpoint="scheduleleaguev2",
        parameters={"LeagueID": "00", "Season": season or current_season()},  # "00" = the NBA
        timeout=TIMEOUT,
    )
    raw = response.get_dict()  # turn the answer into a Python dict

    # If NBA.com sent back something unexpected, stop here with a clear message.
    if not raw.get("leagueSchedule", {}).get("gameDates"):
        raise ValueError("NBA.com answered, but the answer had no games in it")

    CACHE_FILE.parent.mkdir(exist_ok=True)
    CACHE_FILE.write_text(json.dumps(raw), encoding="utf-8")  # utf-8 so Windows reads it the same way
    return raw


def load_schedule():
    """Try to download fresh data. If that fails, fall back to the saved copy."""
    try:
        return download_schedule(), "live (nba_api)"
    except Exception as error:  # a timeout, no internet, NBA.com blocking us, a bad answer...
        if CACHE_FILE.exists():
            return json.loads(CACHE_FILE.read_text(encoding="utf-8")), f"saved copy (download failed: {type(error).__name__})"
        raise RuntimeError(f"nba_api couldn't download the schedule: {type(error).__name__}: {error}") from error


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
