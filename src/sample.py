"""Synthetic game logs shaped exactly like nba_api's LeagueGameLog output.

Used for offline development and tests, and as a fallback when stats.nba.com is
unreachable. Teams use real abbreviations; players and results are made up.
"""
from __future__ import annotations

import datetime as dt

import numpy as np
import pandas as pd

TEAMS = {
    "ATL": "Atlanta Hawks", "BOS": "Boston Celtics", "BKN": "Brooklyn Nets", "CHA": "Charlotte Hornets",
    "CHI": "Chicago Bulls", "CLE": "Cleveland Cavaliers", "DAL": "Dallas Mavericks", "DEN": "Denver Nuggets",
    "DET": "Detroit Pistons", "GSW": "Golden State Warriors", "HOU": "Houston Rockets", "IND": "Indiana Pacers",
    "LAC": "LA Clippers", "LAL": "Los Angeles Lakers", "MEM": "Memphis Grizzlies", "MIA": "Miami Heat",
    "MIL": "Milwaukee Bucks", "MIN": "Minnesota Timberwolves", "NOP": "New Orleans Pelicans",
    "NYK": "New York Knicks", "OKC": "Oklahoma City Thunder", "ORL": "Orlando Magic",
    "PHI": "Philadelphia 76ers", "PHX": "Phoenix Suns", "POR": "Portland Trail Blazers",
    "SAC": "Sacramento Kings", "SAS": "San Antonio Spurs", "TOR": "Toronto Raptors", "UTA": "Utah Jazz",
    "WAS": "Washington Wizards",
}
ABBRS = list(TEAMS)
TEAM_IDS = {a: 1610612700 + i for i, a in enumerate(ABBRS)}

_FIRST = ["Alex", "Jordan", "Marcus", "Tyrese", "Luka", "Devin", "Jalen", "Anthony", "Chris", "Darius",
          "Evan", "Isaiah", "Jamal", "Kevin", "Miles", "Nate", "Owen", "Paul", "Reggie", "Scottie"]
_LAST = ["Adams", "Brooks", "Carter", "Dawson", "Ellis", "Foster", "Grant", "Hayes", "Irving", "Jensen",
         "Knox", "Lowe", "Mercer", "Nolan", "Okafor", "Pierce", "Quinn", "Reyes", "Sutton", "Turner"]

ROSTER_SIZE = 13


def _season_start_year(season: str) -> int:
    return int(season[:4])


def _rosters(rng: np.random.Generator) -> dict[str, list[tuple[int, str, float]]]:
    """(player_id, name, talent) per team. Talent sets minutes and usage."""
    rosters, pid, used = {}, 1_000_000, set()
    for abbr in ABBRS:
        players = []
        for slot in range(ROSTER_SIZE):
            while True:
                name = f"{rng.choice(_FIRST)} {rng.choice(_LAST)}"
                if name not in used:
                    used.add(name)
                    break
            talent = max(0.15, 1.0 - slot * 0.07 + rng.normal(0, 0.08))
            players.append((pid, name, talent))
            pid += 1
        rosters[abbr] = players
    return rosters


def generate(seasons: list[str], seed: int = 7) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (team_games, player_games) for the given seasons."""
    rng = np.random.default_rng(seed)
    rosters = _rosters(rng)
    strength = {a: rng.normal(0, 4.5) for a in ABBRS}
    team_rows, player_rows = [], []
    game_seq = 0

    for season in sorted(seasons):
        start = dt.date(_season_start_year(season), 10, 22)
        season_id = f"2{_season_start_year(season)}"
        # Ratings carry over but regress, like real rosters turning over.
        strength = {a: 0.6 * s + rng.normal(0, 3.5) for a, s in strength.items()}
        pace = {a: rng.normal(99.5, 2.5) for a in ABBRS}
        last_played: dict[str, dt.date] = {}

        for rnd in range(82):
            order = rng.permutation(ABBRS)
            day = start + dt.timedelta(days=int(rnd * 2.1))
            for i in range(0, 30, 2):
                h, a = (order[i], order[i + 1]) if rng.random() < 0.5 else (order[i + 1], order[i])
                gdate = day + dt.timedelta(days=int(rng.integers(0, 2)))
                b2b = {t: last_played.get(t) == gdate - dt.timedelta(days=1) for t in (h, a)}
                exp_margin = strength[h] - strength[a] + 2.5 - 1.5 * b2b[h] + 1.5 * b2b[a]
                margin = int(round(exp_margin + rng.normal(0, 12)))
                if margin == 0:
                    margin = 1 if rng.random() < 0.5 else -1
                poss = (pace[h] + pace[a]) / 2 + rng.normal(0, 3)
                total = poss * 2 * 1.14 + rng.normal(0, 8)
                pts = {h: int(round((total + margin) / 2)), a: int(round((total - margin) / 2))}
                pts[h] = pts[a] + margin
                game_seq += 1
                game_id = f"00{_season_start_year(season) % 100:02d}{game_seq:06d}"
                for team, opp, home in ((h, a, True), (a, h, False)):
                    box = _team_box(rng, pts[team])
                    matchup = f"{team} vs. {opp}" if home else f"{team} @ {opp}"
                    wl = "W" if pts[team] > pts[opp] else "L"
                    team_rows.append({
                        "SEASON_ID": season_id, "TEAM_ID": TEAM_IDS[team], "TEAM_ABBREVIATION": team,
                        "TEAM_NAME": TEAMS[team], "GAME_ID": game_id, "GAME_DATE": gdate.isoformat(),
                        "MATCHUP": matchup, "WL": wl, "MIN": 240, **box,
                        "PLUS_MINUS": pts[team] - pts[opp], "VIDEO_AVAILABLE": 0, "SEASON": season,
                    })
                    player_rows.extend(_player_boxes(rng, rosters[team], box, {
                        "SEASON_ID": season_id, "TEAM_ID": TEAM_IDS[team], "TEAM_ABBREVIATION": team,
                        "TEAM_NAME": TEAMS[team], "GAME_ID": game_id, "GAME_DATE": gdate.isoformat(),
                        "MATCHUP": matchup, "WL": wl, "SEASON": season,
                    }, pts[team] - pts[opp]))
                    last_played[team] = gdate

    team_games = pd.DataFrame(team_rows)
    player_games = pd.DataFrame(player_rows)
    for df in (team_games, player_games):
        df["GAME_DATE"] = pd.to_datetime(df["GAME_DATE"])
        df["SEASON_TYPE"] = "Regular Season"
    return (team_games.sort_values(["GAME_DATE", "GAME_ID"]).reset_index(drop=True),
            player_games.sort_values(["GAME_DATE", "GAME_ID"]).reset_index(drop=True))


def _team_box(rng: np.random.Generator, pts: int) -> dict:
    ftm = int(max(5, rng.normal(17, 4)))
    fg3m = int(max(4, rng.normal(13, 3)))
    fgm = max(20, (pts - ftm - fg3m) // 2)
    ftm = pts - 2 * fgm - fg3m  # keep the box score consistent with the final score
    if ftm < 0:
        fg3m += ftm
        ftm = 0
    fga = int(round(fgm / min(0.6, max(0.38, rng.normal(0.47, 0.04)))))
    fg3a = int(round(fg3m / min(0.5, max(0.25, rng.normal(0.36, 0.05)))))
    fta = int(round(ftm / 0.78)) if ftm else 0
    oreb, dreb = int(max(3, rng.normal(10.5, 3))), int(max(20, rng.normal(33.5, 4)))
    return {
        "FGM": fgm, "FGA": fga, "FG_PCT": round(fgm / fga, 3), "FG3M": fg3m, "FG3A": fg3a,
        "FG3_PCT": round(fg3m / fg3a, 3) if fg3a else 0.0, "FTM": ftm, "FTA": fta,
        "FT_PCT": round(ftm / fta, 3) if fta else 0.0, "OREB": oreb, "DREB": dreb, "REB": oreb + dreb,
        "AST": int(max(12, rng.normal(26, 4))), "STL": int(max(2, rng.normal(8, 2.5))),
        "BLK": int(max(0, rng.normal(5, 2))), "TOV": int(max(5, rng.normal(13.5, 3.5))),
        "PF": int(max(10, rng.normal(19, 3.5))), "PTS": pts,
    }


def _split(rng: np.random.Generator, total: int, weights: np.ndarray) -> np.ndarray:
    if total <= 0:
        return np.zeros(len(weights), dtype=int)
    return rng.multinomial(total, weights / weights.sum())


def _player_boxes(rng, roster, box, base, plus_minus):
    talent = np.array([t for _, _, t in roster])
    playing = rng.random(len(roster)) < np.clip(0.55 + talent * 0.45, 0, 0.99)
    playing[:5] = True
    w = np.where(playing, talent ** 2 * rng.uniform(0.7, 1.3, len(roster)), 0)
    mins = np.where(playing, _split(rng, 240, np.where(playing, talent + 0.5, 0) + 1e-9), 0)
    s = {k: _split(rng, box[k], w + 1e-9) for k in
         ("FGM", "FG3M", "FTM", "OREB", "DREB", "AST", "STL", "BLK", "TOV", "PF")}
    s["FG3M"] = np.minimum(s["FG3M"], s["FGM"])
    rows = []
    for i, (pid, name, _) in enumerate(roster):
        if not playing[i]:
            continue
        fgm, fg3m, ftm = int(s["FGM"][i]), int(s["FG3M"][i]), int(s["FTM"][i])
        fga = fgm + int(rng.poisson(fgm * 1.1 + 0.5))
        fg3a = fg3m + int(rng.poisson(fg3m * 1.7 + 0.3))
        fta = ftm + int(rng.poisson(ftm * 0.28))
        pts = 2 * fgm + fg3m + ftm
        reb = int(s["OREB"][i] + s["DREB"][i])
        rows.append({
            **base, "PLAYER_ID": pid, "PLAYER_NAME": name, "MIN": int(mins[i]),
            "FGM": fgm, "FGA": fga, "FG_PCT": round(fgm / fga, 3) if fga else None,
            "FG3M": fg3m, "FG3A": fg3a, "FG3_PCT": round(fg3m / fg3a, 3) if fg3a else None,
            "FTM": ftm, "FTA": fta, "FT_PCT": round(ftm / fta, 3) if fta else None,
            "OREB": int(s["OREB"][i]), "DREB": int(s["DREB"][i]), "REB": reb,
            "AST": int(s["AST"][i]), "STL": int(s["STL"][i]), "BLK": int(s["BLK"][i]),
            "TOV": int(s["TOV"][i]), "PF": int(s["PF"][i]), "PTS": pts,
            "PLUS_MINUS": int(round(plus_minus * mins[i] / 48 + rng.normal(0, 4))),
            "FANTASY_PTS": round(pts + 1.2 * reb + 1.5 * s["AST"][i] + 3 * (s["STL"][i] + s["BLK"][i])
                                 - s["TOV"][i], 1),
            "VIDEO_AVAILABLE": 0,
        })
    return rows
