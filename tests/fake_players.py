"""Builds made-up player stats in the same shape as NBA.com's leaguedashplayerstats answer.

Goes with fake_schedule.py: the players belong to the same 30 teams, and their games
played and team records fit that schedule, so the MVP code can be tested without internet.
"""
import random

from data import TEAMS, parse_games
from mvp import team_games
from players import COLUMNS
from tests.fake_schedule import fake_schedule

# The player ids of the made-up stars the tests look for (real ids are 6-7 digits;
# these can't clash with them).
STAR_ID = 1           # the best player in the league: should lead the race
INJURED_ID = 2        # as good, but has missed too many games to reach the games rule


def fake_players(seed=2):
    """Six players per team, with per-game averages in a realistic range."""
    rng = random.Random(seed)
    games, _ = parse_games(fake_schedule())
    teams = team_games(games)

    rows = []
    player_id = 100
    for team in TEAMS:
        played = int(teams.loc[team, "played"])
        win_share = teams.loc[team, "wins"] / max(played, 1)
        for slot in range(6):
            player_id += 1
            gp = played - rng.randint(0, 3)          # most players miss a game or two
            w = round(gp * win_share)
            rows.append({
                "PLAYER_ID": player_id, "PLAYER_NAME": f"Player {player_id}", "TEAM_ABBREVIATION": team,
                "AGE": rng.randint(20, 34), "GP": gp, "W": w, "L": gp - w,
                "MIN": round(36 - slot * 3 + rng.uniform(-2, 2), 1),
                "PTS": round(rng.uniform(8, 26) - slot, 1), "REB": round(rng.uniform(2, 10), 1),
                "AST": round(rng.uniform(1, 7), 1), "STL": 1.0, "BLK": 0.5, "TOV": 2.0,
                "FGA": round(rng.uniform(8, 18), 1), "FTA": round(rng.uniform(1, 6), 1),
                "PLUS_MINUS": round(rng.uniform(-6, 6), 1),
            })

    # Two made-up stars on the team with the best record so far: one healthy, one who
    # has missed more games than the rule allows (so he must get a 0% chance).
    best = teams["wins"].idxmax()
    played = int(teams.loc[best, "played"])
    wins = int(teams.loc[best, "wins"])
    star = {"TEAM_ABBREVIATION": best, "AGE": 27, "MIN": 36.0, "PTS": 36.0, "REB": 11.0, "AST": 9.0,
            "STL": 1.5, "BLK": 1.0, "TOV": 3.0, "FGA": 22.0, "FTA": 10.0, "PLUS_MINUS": 12.0}
    rows.append(star | {"PLAYER_ID": STAR_ID, "PLAYER_NAME": "Healthy Star", "GP": played, "W": wins,
                        "L": played - wins})
    rows.append(star | {"PLAYER_ID": INJURED_ID, "PLAYER_NAME": "Injured Star", "GP": 2, "W": 2, "L": 0})

    headers = list(COLUMNS)
    return {"resultSets": [{"headers": headers, "rowSet": [[row[h] for h in headers] for row in rows]}]}
