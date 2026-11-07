"""Builds a small made-up schedule in the same shape as the NBA's file.
Only used by the tests, so they can run without internet."""
import datetime as dt
import random

from data import TEAMS


def team(code, score):
    return {"teamTricode": code, "teamCity": code, "teamName": "Team", "score": score}


def fake_schedule(played_days=70, total_days=160, seed=1):
    rng = random.Random(seed)
    start = dt.date(2026, 10, 20)
    strength = {t: rng.gauss(0, 6) for t in TEAMS}
    game_dates, number = [], 0
    for day in range(total_days):
        date = start + dt.timedelta(days=day)
        teams = TEAMS[:]
        rng.shuffle(teams)
        games = []
        for i in range(0, 10, 2):  # 5 games a day
            home, away = teams[i], teams[i + 1]
            number += 1
            done = day < played_days
            margin = strength[home] - strength[away] + 3 + rng.gauss(0, 12)
            home_score = 110 + round(margin / 2) if done else 0
            away_score = 110 - round(margin / 2) if done else 0
            if done and home_score == away_score:
                home_score += 1
            games.append({
                "gameId": f"00226{number:05d}",
                "gameDateEst": f"{date}T00:00:00Z",
                "gameDateTimeUTC": f"{date}T23:30:00Z",
                "gameStatus": 3 if done else 1,
                "gameStatusText": "Final" if done else "7:30 pm ET",
                "homeTeam": team(home, home_score),
                "awayTeam": team(away, away_score),
            })
        game_dates.append({"games": games})
    return {"leagueSchedule": {"seasonYear": "2026-27", "gameDates": game_dates}}
