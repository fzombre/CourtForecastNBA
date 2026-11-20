"""A second source for the schedule: ESPN, for hosts where stats.nba.com doesn't answer.

Why this exists
---------------
stats.nba.com ignores requests from cloud servers (Vercel, AWS, Google Cloud, ...): it
never answers, and the download times out after 30 seconds. NBA.com's public file server
(cdn.nba.com) now refuses programs too, everywhere. ESPN's public scoreboard feed answers
from anywhere, so the deployed API gets live scores from ESPN instead.

On your own PC nothing changes: data.load_schedule() still asks NBA.com first and only
falls back to ESPN if that fails. See data.py for the order.

How it works
------------
ESPN's scoreboard feed accepts a whole month: ...?dates=202611 returns every game in
November 2026 (finished ones with scores, upcoming ones with their start time). A
season runs from October (preseason) to June (the Finals), so 9 requests, sent at the
same time, cover all of it.

Each ESPN game is then rewritten in exactly the shape of NBA.com's schedule file, so
data.parse_games() and everything after it (standings, the model, the simulation, the
website) work on it unchanged. That rewriting (to_nba_game) is the part to fix if ESPN
ever changes its feed; tests/test_espn.py checks it on a small sample.

The feed is unofficial: ESPN doesn't document it, and could change it without notice.
It's widely used and has been stable for years, but if downloads start failing with
KeyError or the like, this file is where to look.
"""
import datetime as dt
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
import requests

SCOREBOARD_URL = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"
TIMEOUT = 20  # seconds per request; ESPN normally answers in about one

# ESPN writes six team codes differently from NBA.com. Every other team uses the same
# three letters on both. Codes that aren't NBA teams at all (All-Star teams like "STARS",
# overseas preseason opponents) pass through unchanged, and data.parse_games() skips them.
ESPN_TO_NBA = {"GS": "GSW", "NO": "NOP", "NY": "NYK", "SA": "SAS", "UTAH": "UTA", "WSH": "WAS"}

# ESPN's season types -> the stage digit NBA.com puts third in a game id (see
# data.STAGES): "1" preseason, "2" regular season, "4" playoffs, "5" play-in.
# ESPN has no type for the NBA Cup final (it's a regular-season game with the note
# "NBA Cup Championship"), so that one is recognized by its note in stage_digit().
SEASON_TYPE_TO_STAGE = {1: "1", 2: "2", 3: "4", 5: "5"}

# The months a season's games fall in: preseason starts in early October, the Finals end in June.
SEASON_MONTHS = [10, 11, 12, 1, 2, 3, 4, 5, 6]

# Months that are over, with every game final, never change again. We keep them here
# (in memory, for as long as the app runs) and only download the other months on the
# next refresh. Key: "202611", value: that month's list of ESPN events.
_finished_months = {}


def season_months(season):
    """'2026-27' -> ['202610', '202611', '202612', '202701', ..., '202706']."""
    first_year = int(season[:4])
    return [f"{first_year if month >= 7 else first_year + 1}{month:02d}" for month in SEASON_MONTHS]


def download_month(session, month):
    """Every game ESPN lists for one month (a list of ESPN "events")."""
    response = session.get(SCOREBOARD_URL, params={"dates": month, "limit": 1000}, timeout=TIMEOUT)
    response.raise_for_status()  # an HTTP error (403, 500, ...) becomes an exception here
    return response.json().get("events", [])


def month_is_finished(month, events, today=None):
    """True if the month is over and every game in it is final: it can't change any more."""
    today = today or dt.date.today()
    year, number = int(month[:4]), int(month[4:])
    first_of_next = dt.date(year + number // 12, number % 12 + 1, 1)
    return today >= first_of_next and all(event["status"]["type"].get("completed") for event in events)


def score_of(competitor):
    """A team's points. The scoreboard sends "121"; some ESPN feeds send {"value": 121.0}."""
    score = competitor.get("score")
    if isinstance(score, dict):
        score = score.get("value")
    try:
        return int(float(score))
    except (TypeError, ValueError):
        return 0  # no score yet


def stage_digit(event):
    """The NBA.com stage digit for an ESPN game (see SEASON_TYPE_TO_STAGE), "9" if unknown."""
    notes = " ".join(note.get("headline", "") for note in event["competitions"][0].get("notes", []))
    if "cup" in notes.lower() and "championship" in notes.lower():
        return "6"  # the NBA Cup final: doesn't count in the standings, like on NBA.com
    return SEASON_TYPE_TO_STAGE.get(event.get("season", {}).get("type"), "9")


def start_time_text(start_et, time_known):
    """'7:30 pm ET', the way NBA.com writes a start time; 'TBD' if ESPN has no time yet."""
    if not time_known:
        return "TBD"
    hour = start_et.hour % 12 or 12   # 19 -> 7, 0 -> 12
    am_pm = "am" if start_et.hour < 12 else "pm"
    return f"{hour}:{start_et.minute:02d} {am_pm} ET"


def to_nba_game(event):
    """One ESPN event -> one game in the shape of NBA.com's schedule file.

    These are the fields data.parse_games() reads. ESPN ids are kept, with the stage digit
    in front ("002E401910017"): the app uses a game id only to tell games apart and, via
    its third character, to know the stage.
    """
    competition = event["competitions"][0]
    status = competition.get("status") or event["status"]
    status_type = status["type"]
    start_utc = pd.Timestamp(event["date"])                    # "2026-11-21T03:00Z"
    start_et = start_utc.tz_convert("America/New_York")      # 10:00 pm on Nov 20 in New York

    if status_type.get("completed"):
        game_status, text = 3, status_type.get("shortDetail", "Final")     # "Final", "Final/OT"
    elif status_type.get("state") == "in":
        game_status, text = 2, status_type.get("shortDetail", "Live")      # "5:12 - 3rd", "Halftime"
    elif status_type.get("state") == "post":
        game_status, text = 1, status_type.get("description", "Postponed")  # postponed or canceled
    else:
        game_status, text = 1, start_time_text(start_et, event.get("timeValid", True))

    teams = {}
    for competitor in competition["competitors"]:
        team = competitor.get("team", {})
        code = team.get("abbreviation", "")   # missing for some overseas preseason opponents
        teams[competitor["homeAway"]] = {
            "teamTricode": ESPN_TO_NBA.get(code, code),
            "teamCity": team.get("location", ""),
            "teamName": team.get("name", ""),
            "score": score_of(competitor),
        }

    notes = competition.get("notes", [])
    return {
        "gameId": f"00{stage_digit(event)}E{event['id']}",
        "gameDateTimeUTC": start_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "gameDateEst": f"{start_et.date().isoformat()}T00:00:00Z",   # parse_games reads the first 10 characters
        "gameLabel": notes[0].get("headline", "") if notes else "",     # e.g. "NBA Cup - Group Play"
        "gameStatus": game_status,
        "gameStatusText": text,
        "homeTeam": teams.get("home", {}),
        "awayTeam": teams.get("away", {}),
    }


def download_schedule(season):
    """The whole season from ESPN, rewritten in the shape of NBA.com's schedule file.

    season: "2026-27" (data.current_season()). Returns
        {"leagueSchedule": {"seasonYear": "2026-27", "gameDates": [{"games": [...]}]}}
    All games sit in one "gameDates" entry; parse_games() sorts them by start time anyway.
    """
    months = season_months(season)
    to_download = [month for month in months if month not in _finished_months]

    # The months are independent, so ask for all of them at once (about 1-2 s in total
    # instead of 9 one after another). A Session reuses one connection to ESPN.
    with requests.Session() as session, ThreadPoolExecutor(max_workers=len(months)) as pool:
        downloaded = dict(zip(to_download, pool.map(lambda month: download_month(session, month), to_download)))

    for month, events in downloaded.items():
        if month_is_finished(month, events):
            _finished_months[month] = events

    end_year = int(season[:4]) + 1   # ESPN names a season by the year it ends: 2026-27 is 2027
    games = []
    for month in months:
        events = _finished_months.get(month) or downloaded.get(month, [])
        for event in events:
            if event.get("season", {}).get("year", end_year) == end_year:
                games.append(to_nba_game(event))

    if not games:
        raise ValueError("ESPN answered, but listed no games for this season")
    return {"leagueSchedule": {"seasonYear": season, "gameDates": [{"games": games}]}}
