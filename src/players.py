"""Player stats: every player's season averages, for the MVP race (see mvp.py).

data.py downloads the *schedule* (team results). This file is its twin for *players*:
the same idea, the same safety nets, a different endpoint.

We use nba_api's "leaguedashplayerstats" endpoint. One request returns one row per
player who has played this season, with his per-game averages: points, rebounds,
assists, shooting, plus/minus, and the record of his team in the games he played.
That's the same table NBA.com shows at nba.com/stats/players/traditional.

Like the schedule, every successful download is saved to disk (data/players.json),
so the MVP tab still works when stats.nba.com is slow or blocks us.

The snapshot: player stats on hosts where NBA.com doesn't answer
----------------------------------------------------------------
The schedule has a second source (ESPN, see espn.py), but player stats don't: ESPN's
feed has no league-wide season averages in NBA.com's form. So on hosts where
stats.nba.com ignores us (Vercel; see data.stats_nba_blocked), the API reads
data/players_snapshot.json instead. That file is downloaded on your own PC, where
NBA.com does answer, by scripts/update_data.py, and pushed to GitHub with the code.
Unlike data/players.json (a private copy each computer keeps for itself), the snapshot
is committed to git, so the deployed site gets it. Season averages barely move from
one game to the next, so updating it once a day keeps the MVP tab accurate.

Every player-stats answer carries a "saved_at" time (when it was downloaded, in UTC), so
the MVP tab can say how fresh its numbers are.
"""
import datetime as dt
import json
from pathlib import Path

import pandas as pd
from nba_api.stats.endpoints import leaguedashplayerstats

from data import TIMEOUT, current_season, stats_nba_blocked

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CACHE_FILE = DATA_DIR / "players.json"              # this computer's own copy (not in git)
SNAPSHOT_FILE = DATA_DIR / "players_snapshot.json"  # the copy the deployed site uses (in git)

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
    # When we got it, in UTC, e.g. "2026-11-19T23:40:12Z" (see the module docstring).
    raw["saved_at"] = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return raw


def read_json(path):
    """A saved player-stats file, or None if it doesn't exist."""
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def write_snapshot(raw, path=SNAPSHOT_FILE):
    """Save a download as the snapshot the deployed site reads (scripts/update_data.py calls this).

    Only the COLUMNS we use are kept (NBA.com sends ~70 per player, mostly rankings), which
    makes the file about 4 times smaller. Each player goes on his own line, so when the
    snapshot is updated, `git diff` (and git's storage) only deal with the lines that changed.
    """
    table = raw["resultSets"][0]
    keep = [table["headers"].index(column) for column in COLUMNS]
    rows = [json.dumps([row[i] for i in keep], ensure_ascii=False) for row in table["rowSet"]]
    text = ("{\n"
            f'"saved_at": {json.dumps(raw.get("saved_at"))},\n'
            f'"season": {json.dumps(current_season())},\n'
            f'"resultSets": [{{"headers": {json.dumps(list(COLUMNS))}, "rowSet": [\n'
            + ",\n".join(rows)
            + "\n]}]\n}\n")
    path.parent.mkdir(exist_ok=True)
    path.write_text(text, encoding="utf-8")  # utf-8, and ensure_ascii=False above: "Jokić" stays readable


def load_player_stats():
    """This season's player stats, from the best place available. Returns (raw, source).

    On hosts where NBA.com doesn't answer (Vercel): the snapshot, straight away.
    Everywhere else, the first of these that works:
      1. a fresh download from NBA.com              -> source "live (nba_api)"
      2. this computer's saved copy of the last one -> "saved copy (...)"
      3. the snapshot                               -> "snapshot (...)"
    """
    if stats_nba_blocked():
        snapshot = read_json(SNAPSHOT_FILE)
        if snapshot is None:
            raise RuntimeError("No player-stats snapshot to read. On your PC, run "
                               "`python scripts/update_data.py`, then commit and push data/players_snapshot.json")
        return snapshot, "snapshot"

    try:
        raw = download_player_stats()
    except Exception as error:  # timeout, no internet, NBA.com blocking us, a bad answer...
        failure = f"download failed: {type(error).__name__}"
        for path, source in [(CACHE_FILE, f"saved copy ({failure})"), (SNAPSHOT_FILE, f"snapshot ({failure})")]:
            saved = read_json(path)
            if saved is not None:
                return saved, source
        raise RuntimeError(f"nba_api couldn't download player stats: {type(error).__name__}: {error}") from error

    # Save a copy for when a later download fails. Some hosts don't let the app write to
    # its own folder; there we keep the fresh data and just skip the copy. (This is outside
    # the try above on purpose: a failed save must not throw away a download that worked,
    # the way an exception inside that try would.)
    try:
        CACHE_FILE.parent.mkdir(exist_ok=True)
        CACHE_FILE.write_text(json.dumps(raw), encoding="utf-8")  # utf-8: names have accents
    except OSError:
        pass
    return raw, "live (nba_api)"


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
