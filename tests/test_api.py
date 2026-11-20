"""Checks that every API endpoint answers with sensible JSON.

Like test_basics.py, this uses the made-up schedule from fake_schedule.py,
so it runs without the internet and never touches stats.nba.com.
"""
import pytest
from fastapi.testclient import TestClient

import api
from tests.fake_players import STAR_ID, fake_players
from tests.fake_schedule import fake_schedule


@pytest.fixture
def client(monkeypatch):
    # Swap the real download for the fake schedule. api.py imported load_schedule
    # by name, so that name inside api is the one we replace.
    monkeypatch.setattr(api, "load_schedule", lambda: (fake_schedule(), "test data"))
    monkeypatch.setattr(api, "load_player_stats", lambda: (fake_players(), "test players"))  # same idea, for the MVP tab
    # Fewer simulations than the real app, so the tests run quickly. The odds still have
    # to add up exactly (one champion per season), whatever the number of simulations.
    monkeypatch.setattr(api, "N_SIMS", 500)
    api.refresh()  # start every test with empty caches
    return TestClient(api.app)


def test_overview(client):
    body = client.get("/api/overview").json()
    assert body["season"] == "2026-27"
    assert body["source"] == "test data"
    assert body["n_sims"] == 500  # the app's own setting (500 here, set by the fixture above)
    assert len(body["ratings"]) == 30
    assert body["team_ids"]["BOS"] == 1610612738  # used for the team logos
    assert len(body["team_ids"]) == 30


def test_results_and_upcoming(client):
    assert len(client.get("/api/results").json()) == 350  # 70 days x 5 games already played
    upcoming = client.get("/api/upcoming").json()
    assert all(0 <= game["home_win_prob"] <= 1 for game in upcoming)
    assert upcoming[0]["date"] == "2026-12-29"  # plain "YYYY-MM-DD" text, easy for TypeScript


def test_standings(client):
    body = client.get("/api/standings").json()
    assert len(body["East"]) == len(body["West"]) == 15
    assert body["East"][0]["GB"] == 0  # the leader is 0 games behind itself


def test_projected_standings(client):
    body = client.get("/api/projected-standings", params={"date": "2027-02-01"}).json()
    assert body["date"] == "2027-02-01"
    assert len(body["East"]) == 15
    assert client.get("/api/projected-standings", params={"date": "not a date"}).status_code == 422


def test_projected_standings_default_date(client):
    # Without a date, the API picks the first option and lists all of them for the date picker.
    body = client.get("/api/projected-standings").json()
    assert body["date"] == body["date_options"][0]
    assert body["date_options"] == sorted(body["date_options"])  # earliest first
    assert body["date_options"][-1] == "2027-03-28"  # last day of the made-up regular season


def test_odds_add_up(client):
    odds = client.get("/api/odds").json()
    assert abs(sum(team["champion"] for team in odds) - 100) < 0.5  # exactly one champion per season


def test_mvp(client):
    body = client.get("/api/mvp").json()
    assert body["source"] == "test players"
    assert body["backtest"]["seasons"] == 30
    assert [w["feature"] for w in body["weights"]] == ["pts", "reb", "ast", "ts_pct", "plus_minus", "win_pct"]

    candidates = body["candidates"]
    assert 0 < len(candidates) <= api.MVP_MAX_ROWS
    assert candidates[0]["player_id"] == STAR_ID          # the made-up star leads
    chances = [c["chance"] for c in candidates]
    assert chances == sorted(chances, reverse=True)         # best chance first
    assert sum(chances) <= 100.01
    # Players not on track for the games rule have no ladder rank: null in JSON, not NaN.
    assert all(c["rank"] is None or c["rank"] >= 1 for c in candidates)
