"""Checks that every API endpoint answers with sensible JSON.

Like test_basics.py, this uses the made-up schedule from fake_schedule.py,
so it runs without the internet and never touches stats.nba.com.
"""
import pytest
from fastapi.testclient import TestClient

import api
from tests.fake_schedule import fake_schedule


@pytest.fixture
def client(monkeypatch):
    # Swap the real download for the fake schedule. api.py imported load_schedule
    # by name, so that name inside api is the one we replace.
    monkeypatch.setattr(api, "load_schedule", lambda: (fake_schedule(), "test data"))
    api.refresh()  # start every test with empty caches
    return TestClient(api.app)


def test_overview(client):
    body = client.get("/api/overview").json()
    assert body["season"] == "2026-27"
    assert body["source"] == "test data"
    assert len(body["ratings"]) == 30


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
    assert len(body["East"]) == 15
    assert client.get("/api/projected-standings", params={"date": "not a date"}).status_code == 422


def test_odds_add_up(client):
    odds = client.get("/api/odds", params={"sims": 500}).json()
    assert abs(sum(team["champion"] for team in odds) - 100) < 0.5  # exactly one champion per season
