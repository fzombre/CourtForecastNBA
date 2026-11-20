"""Player stats: every player's season averages, for the MVP race (see mvp.py).

data.py downloads the *schedule* (team results). This file is its twin for *players*:
the same idea, the same safety nets, a different endpoint.

We use nba_api's "leaguedashplayerstats" endpoint. One request returns one row per
player who has played this season, with his per-game averages: points, rebounds,
assists, shooting, plus/minus, and the record of his team in the games he played.
That's the same table NBA.com shows at nba.com/stats/players/traditional.

Like the schedule, every successful download is saved to disk (data/players.json),
so the MVP tab still works when stats.nba.com is slow or blocks us.
"""
import json
from pathlib import Path

import pandas as pd
from nba_api.stats.endpoints import leaguedashplayerstats

from data import TIMEOUT, current_season

CACHE_FILE = Path(__file__).resolve().parent.parent / "data" / "players.json"  # next to schedule.json

# The columns we keep from NBA.com's table, and the shorter lowercase names we give them
# (lowercase like the games table in data.py). NBA.com sends ~70 columns, most of them
# rankings ("PTS_RANK", ...) that we don't need.
COLUMNS = {
    "PLAYER_ID": "player_id",          # NBA.com's id for the player, e.g. 1628983 (also used for his photo)
    "PLAYER_NAME": "name",             # "Shai Gilgeous-Alexander" (with accents: "Nikola Jokić")
    "TEAM_ABBREVIATION": "team",       # his current team; a traded player shows his latest team
    "AGE": "age",
    "GP": "gp",                        # games played
    "W": "w",                          # his team's wins in the games HE played
    "L": "l",                          # ... and losses
    "MIN": "min",                      # minutes per game
    "PTS": "pts",                      # points per game
    "REB": "reb",                      # rebounds per game
    "AST": "ast",                      # assists per game
    "STL": "stl",                      # steals per game
    "BLK": "blk",                      # blocks per game
    "TOV": "tov",                      # turnovers per game
    "FGA": "fga",                      # field-goal attempts per game (for true shooting below)
    "FTA": "fta",                      # free-throw attempts per game (for true shooting below)
    "PLUS_MINUS": "plus_minus",        # points his team outscored opponents by while he was on court, per game
}


def download_player_stats(season=None, timeout=TIMEOUT):
    """Ask stats.nba.com for every player's per-game averages in one regular season.

    Returns NBA.com's raw answer (a dict) that parse_player_stats() understands:
        {"resultSets": [{"headers": ["PLAYER_ID", ...], "rowSet": [[1628983, ...], ...]}]}

    nba_api's LeagueDashPlayerStats class fills in the ~30 filter parameters the endpoint
    insists on (all of them "no filter"), so we only set the ones we care about.
    Creating the object is what sends the request.
    """
    endpoint = leaguedashplayerstats.LeagueDashPlayerStats(
        season=season or current_season(),
        season_type_all_star="Regular Season",  # the MVP is a regular-season award
        per_mode_detailed="PerGame",             # averages per game, not season totals
        timeout=timeout,
    )
    raw = endpoint.get_dict()
    if not raw.get("resultSets") or not raw["resultSets"][0].get("rowSet"):
        raise ValueError("NBA.com answered, but the answer had no players in it")
    return raw


def load_player_stats():
    """This season's player stats: a fresh download if possible, otherwise the saved copy.

    Returns (raw, source), exactly like data.load_schedule(), so api.py can say where the
    numbers came from.
    """
    try:
        raw = download_player_stats()
        CACHE_FILE.parent.mkdir(exist_ok=True)
        CACHE_FILE.write_text(json.dumps(raw), encoding="utf-8")  # utf-8: names have accents
        return raw, "live (nba_api)"
    except Exception as error:  # timeout, no internet, NBA.com blocking us, a bad answer...
        if CACHE_FILE.exists():
            return (json.loads(CACHE_FILE.read_text(encoding="utf-8")),
                    f"saved copy (download failed: {type(error).__name__})")
        raise RuntimeError(f"nba_api couldn't download player stats: {type(error).__name__}: {error}") from error


def parse_player_stats(raw):
    """Turn NBA.com's answer into a DataFrame with one row per player and our column names.

    Also adds two columns the MVP model uses:
      - ts_pct:  true shooting %, the standard "how efficiently does he score" number. It
                 counts threes and free throws fairly: points / (2 * (FGA + 0.44 * FTA)).
                 (0.44 is the usual estimate of how many possessions a free throw uses.)
      - win_pct: his team's win % in the games he played, W / (W + L).
    """
    table = raw["resultSets"][0]
    players = pd.DataFrame(table["rowSet"], columns=table["headers"])
    players = players[list(COLUMNS)].rename(columns=COLUMNS)

    shooting_possessions = 2 * (players["fga"] + 0.44 * players["fta"])
    # A player who never took a shot would divide by zero; give him 0 instead of NaN.
    players["ts_pct"] = (players["pts"] / shooting_possessions.where(shooting_possessions > 0)).fillna(0.0)
    players["win_pct"] = players["w"] / (players["w"] + players["l"]).where(players["gp"] > 0)
    players["win_pct"] = players["win_pct"].fillna(0.0)
    return players
