"""Builds data/mvp_history.csv: the past seasons the MVP model learns from.

Run it from the project folder with:
    python scripts/build_mvp_history.py

What it does, for every season in mvp.MVP_WINNERS (1996-97 to last season):
  1. downloads every player's per-game averages from stats.nba.com (players.py),
  2. keeps the players who were regulars (see KEEP_* below), so the file stays small,
  3. marks the one player who actually won MVP that season (mvp = 1, everyone else 0).

Past seasons never change, so this only needs running once a year, after a new MVP is
announced: add the winner to MVP_WINNERS in src/mvp.py and run this again. The CSV is
committed to git, so the app (and the tests) never need to download 30 seasons.

It takes about a minute: one request per season, with a pause in between so we don't
hammer stats.nba.com (it blocks clients that ask too fast).
"""
import sys
import time
import unicodedata
from pathlib import Path

# Let this script import from src/, like the app does.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import pandas as pd  # noqa: E402  (imports after the sys.path line on purpose)

from mvp import HISTORY_FILE, MVP_WINNERS  # noqa: E402
from players import download_player_stats, parse_player_stats  # noqa: E402

# Only regulars go in the file. Nobody has won MVP playing under 30 minutes a game or
# in under ~60% of the season, so these filters are loose: they only drop bench players
# and players who barely played, and keep plenty of "didn't win" examples for the model.
KEEP_MIN_MINUTES = 20
KEEP_MIN_GAMES = 20

PAUSE_SECONDS = 1.5   # between requests, to be polite to stats.nba.com
RETRIES = 3           # NBA.com sometimes times out once; try a season again before giving up

# The columns saved to the CSV (the ones the MVP model and the tests use, plus a few
# to read the file by eye). Rounded below so the file is small and diffs are readable.
SAVED = ["season", "player_id", "name", "team", "age", "gp", "w", "l", "min",
         "pts", "reb", "ast", "stl", "blk", "tov", "ts_pct", "plus_minus", "win_pct", "mvp"]


def plain(name):
    """'Nikola Jokić' -> 'nikola jokic': drop accents and case, so names match reliably.

    NFKD splits "ć" into "c" + a separate accent mark; we then throw the accent marks away.
    """
    decomposed = unicodedata.normalize("NFKD", name)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch)).lower().strip()


def download_season(season):
    """One season's player table, retrying a couple of times if NBA.com is slow."""
    for attempt in range(1, RETRIES + 1):
        try:
            return parse_player_stats(download_player_stats(season))
        except Exception as error:
            if attempt == RETRIES:
                raise
            print(f"  {season}: {type(error).__name__}, trying again...")
            time.sleep(PAUSE_SECONDS * 3)


def main():
    seasons = []
    for season, winner in MVP_WINNERS.items():
        players = download_season(season)
        players = players[(players["min"] >= KEEP_MIN_MINUTES) & (players["gp"] >= KEEP_MIN_GAMES)].copy()
        players.insert(0, "season", season)

        # Mark the winner. Stop with a clear message if the name doesn't match exactly one
        # player: a silent miss would teach the model that season had no MVP.
        players["mvp"] = (players["name"].map(plain) == plain(winner)).astype(int)
        if players["mvp"].sum() != 1:
            raise SystemExit(f"{season}: expected exactly one player named {winner!r}, "
                             f"found {players['mvp'].sum()}")

        seasons.append(players)
        print(f"{season}: {len(players):3d} regulars, MVP {winner}")
        time.sleep(PAUSE_SECONDS)

    history = pd.concat(seasons)[SAVED].round(3)
    HISTORY_FILE.parent.mkdir(exist_ok=True)
    history.to_csv(HISTORY_FILE, index=False, encoding="utf-8")
    print(f"\nSaved {len(history)} rows from {len(seasons)} seasons to {HISTORY_FILE}")


if __name__ == "__main__":
    main()
