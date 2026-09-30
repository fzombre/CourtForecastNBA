"""Loading NBA game logs from stats.nba.com (via nba_api), with a local CSV cache.

Everything in the app is derived from two league-wide game logs per season:
one row per team per game, and one row per player per game.
"""
from __future__ import annotations

import datetime as dt
import os
import time
from pathlib import Path

import pandas as pd

CACHE_DIR = Path(os.environ.get("FRANK_CACHE_DIR", Path(__file__).resolve().parent.parent / "data"))

# Refetch the in-progress season's cache after this many hours; finished seasons never change.
CURRENT_SEASON_TTL_HOURS = 6


def season_str(start_year: int) -> str:
    """2025 -> '2025-26'."""
    return f"{start_year}-{str(start_year + 1)[-2:]}"


def current_season_start_year(today: dt.date | None = None) -> int:
    today = today or dt.date.today()
    # The regular season tips off in October; before that the latest season is last year's.
    return today.year if today.month >= 10 else today.year - 1


def recent_seasons(n: int, today: dt.date | None = None) -> list[str]:
    last = current_season_start_year(today)
    return [season_str(y) for y in range(last - n + 1, last + 1)]


def _cache_path(season: str, kind: str, season_type: str) -> Path:
    tag = "po" if season_type == "Playoffs" else "rs"
    return CACHE_DIR / f"{season}_{kind}_{tag}.csv"


def _is_fresh(path: Path, season: str) -> bool:
    if not path.exists():
        return False
    if season != season_str(current_season_start_year()):
        return True
    age_h = (time.time() - path.stat().st_mtime) / 3600
    return age_h < CURRENT_SEASON_TTL_HOURS


def _fetch_game_log(season: str, kind: str, season_type: str, retries: int = 3) -> pd.DataFrame:
    from nba_api.stats.endpoints import leaguegamelog

    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            resp = leaguegamelog.LeagueGameLog(
                season=season,
                player_or_team_abbreviation=kind,
                season_type_all_star=season_type,
                timeout=60,
            )
            return resp.get_data_frames()[0]
        except Exception as err:  # stats.nba.com is flaky and rate limits aggressively
            last_err = err
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"Could not download {season} game log from stats.nba.com: {last_err}")


def load_game_log(season: str, kind: str = "T", season_type: str = "Regular Season",
                  force: bool = False) -> pd.DataFrame:
    """kind='T' for team games, 'P' for player games."""
    path = _cache_path(season, kind, season_type)
    if not force and _is_fresh(path, season):
        df = pd.read_csv(path)
    else:
        df = _fetch_game_log(season, kind, season_type)
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        df.to_csv(path, index=False)
    if not df.empty:
        df["GAME_DATE"] = pd.to_datetime(df["GAME_DATE"])
        df["SEASON"] = season
        df["SEASON_TYPE"] = season_type
    return df


def load_seasons(seasons: list[str], kind: str = "T", include_playoffs: bool = False,
                 force: bool = False) -> pd.DataFrame:
    frames = []
    types = ["Regular Season", "Playoffs"] if include_playoffs else ["Regular Season"]
    for season in seasons:
        for st in types:
            df = load_game_log(season, kind, st, force=force)
            if not df.empty:
                frames.append(df)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True).sort_values(["GAME_DATE", "GAME_ID"]).reset_index(drop=True)


def team_games_to_matchups(team_games: pd.DataFrame) -> pd.DataFrame:
    """Pair the two team rows of each game into one row: home team vs away team."""
    tg = team_games.copy()
    tg["IS_HOME"] = tg["MATCHUP"].str.contains(" vs. ")
    home = tg[tg["IS_HOME"]].set_index("GAME_ID")
    away = tg[~tg["IS_HOME"]].set_index("GAME_ID")
    games = home[["GAME_DATE", "SEASON", "SEASON_TYPE", "TEAM_ABBREVIATION", "PTS"]].join(
        away[["TEAM_ABBREVIATION", "PTS"]], rsuffix="_AWAY", how="inner"
    )
    games = games.rename(columns={"TEAM_ABBREVIATION": "HOME", "PTS": "HOME_PTS",
                                  "TEAM_ABBREVIATION_AWAY": "AWAY", "PTS_AWAY": "AWAY_PTS"})
    games["MARGIN"] = games["HOME_PTS"] - games["AWAY_PTS"]
    games["HOME_WIN"] = (games["MARGIN"] > 0).astype(int)
    return games.reset_index().sort_values(["GAME_DATE", "GAME_ID"]).reset_index(drop=True)
