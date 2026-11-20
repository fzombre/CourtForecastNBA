"""Checks for the second data sources: ESPN's schedule (espn.py), the order data.py tries
its sources in, and the player-stats snapshot (players.py).

The ESPN tests use small hand-built games in the shape of ESPN's scoreboard feed (the
fields espn.py reads, as seen in real answers), covering every awkward case: overtime,
a live game, the NBA Cup final, the play-in, the playoffs, All-Star, an overseas
preseason opponent without a team code, a postponed game and a start time ESPN doesn't
know yet. Nothing here touches the internet or your real data/ folder.
"""
import json

import pytest

import data
import espn
import players
from data import parse_games
from tests.fake_players import fake_players


def competitor(home_away, code, location, name, score=None):
    """One team in an ESPN game, as the scoreboard sends it (scores are text)."""
    team = {"location": location, "name": name}
    if code is not None:
        team["abbreviation"] = code
    entry = {"homeAway": home_away, "team": team}
    if score is not None:
        entry["score"] = str(score)
    return entry


def event(event_id, date, home, away, *, season_type=2, state="post", completed=True,
          detail="Final", notes=(), time_valid=True, year=2027):
    """One ESPN game. home/away: (code, location, name, score)."""
    return {
        "id": event_id,
        "date": date,
        "timeValid": time_valid,
        "season": {"year": year, "type": season_type},
        "status": {"type": {"state": state, "completed": completed, "shortDetail": detail,
                            "description": detail}},
        "competitions": [{
            "competitors": [competitor("home", *home), competitor("away", *away)],
            "notes": [{"headline": note} for note in notes],
        }],
    }


GSW = ("GS", "Golden State", "Warriors")
NYK = ("NY", "New York", "Knicks")
LAL = ("LAL", "Los Angeles", "Lakers")
UTA = ("UTAH", "Utah", "Jazz")
BOS = ("BOS", "Boston", "Celtics")
SAS = ("SA", "San Antonio", "Spurs")

SAMPLE = [
    # A finished overtime game. 03:00 UTC on Nov 19 is 10 pm on Nov 18 in New York.
    event("1", "2026-11-19T03:00Z", GSW + (121,), NYK + (118,), detail="Final/OT"),
    # Being played right now.
    event("2", "2026-11-20T00:30Z", LAL + (55,), UTA + (61,), state="in", completed=False, detail="5:12 - 3rd"),
    # Not started yet: an NBA Cup group game at 7:30 pm ET.
    event("3", "2026-11-21T00:30Z", BOS + (0,), SAS + (0,), state="pre", completed=False,
          detail="11/20 - 7:30 PM EST", notes=["NBA Cup - Group Play"]),
    # A start time ESPN doesn't know yet.
    event("4", "2027-04-10T23:00Z", NYK + (0,), BOS + (0,), state="pre", completed=False, detail="TBD",
          time_valid=False),
    # Postponed: over ("post") but never completed.
    event("5", "2026-12-01T00:00Z", SAS + (0,), LAL + (0,), state="post", completed=False, detail="Postponed"),
    # The NBA Cup final, the play-in, a playoff game, preseason.
    event("6", "2026-12-16T01:30Z", NYK + (110,), SAS + (100,), notes=["NBA Cup Championship"]),
    event("7", "2027-04-15T23:30Z", GSW + (101,), LAL + (99,), season_type=5,
          notes=["NBA Play-In - West - 7th Place vs 8th Place"]),
    event("8", "2027-04-19T23:00Z", BOS + (112,), NYK + (104,), season_type=3, notes=["East 1st Round - Game 1"]),
    event("9", "2026-10-05T23:00Z", LAL + (120,), UTA + (98,), season_type=1),
    # Not NBA teams: All-Star, and an overseas preseason opponent with no team code at all.
    event("10", "2027-02-15T01:00Z", ("STARS", "Stars", "Stars", 150), ("WORLD", "World", "World", 140),
          notes=["NBA All-Star - Championship"]),
    event("11", "2026-10-03T18:00Z", BOS + (130,), (None, "Melbourne", "United", 90), season_type=1),
    # Last season's game in the same month: must be left out.
    event("12", "2026-06-10T00:30Z", BOS + (100,), SAS + (90,), season_type=3, year=2026),
]


def as_schedule(events):
    """Turn sample events into data.parse_games() input, like espn.download_schedule() does."""
    games = [espn.to_nba_game(e) for e in events if e["season"]["year"] == 2027]
    return {"leagueSchedule": {"seasonYear": "2026-27", "gameDates": [{"games": games}]}}


@pytest.fixture
def games():
    table, season = parse_games(as_schedule(SAMPLE))
    assert season == "2026-27"
    return table.set_index(table["game_id"].str[3:].str.lstrip("E"))  # index by ESPN id: "1", "2", ...


def test_season_months():
    assert espn.season_months("2026-27") == ["202610", "202611", "202612", "202701", "202702",
                                             "202703", "202704", "202705", "202706"]


def test_team_codes_names_and_scores(games):
    game = games.loc["1"]
    assert (game["home"], game["away"]) == ("GSW", "NYK")           # ESPN "GS"/"NY" -> NBA.com codes
    assert game["home_name"] == "Golden State Warriors"
    assert (game["home_score"], game["away_score"]) == (121, 118)
    assert game["played"] and game["winner"] == "GSW"
    assert game["status_text"] == "Final/OT"
    assert str(game["date"]) == "2026-11-18"                          # the US Eastern date, not UTC's Nov 19


def test_status_of_live_upcoming_postponed_and_tbd_games(games):
    assert (games.loc["2", "status"], games.loc["2", "status_text"]) == (2, "5:12 - 3rd")
    assert not games.loc["2", "played"]
    assert (games.loc["3", "status"], games.loc["3", "status_text"]) == (1, "7:30 pm ET")
    assert games.loc["3", "label"] == "NBA Cup - Group Play"
    assert games.loc["4", "status_text"] == "TBD"
    assert (games.loc["5", "status"], games.loc["5", "status_text"]) == (1, "Postponed")


def test_stages(games):
    assert games.loc["1", "stage"] == "Regular Season"
    assert games.loc["6", "stage"] == "NBA Cup Final"     # doesn't count in the standings, like on NBA.com
    assert games.loc["7", "stage"] == "Play-In"
    assert games.loc["8", "stage"] == "Playoffs"
    assert games.loc["9", "stage"] == "Preseason"


def test_non_nba_games_and_other_seasons_are_left_out(games):
    assert "10" not in games.index   # All-Star teams
    assert "11" not in games.index   # overseas opponent without a team code
    assert "12" not in games.index   # last season's Finals game
    assert len(games) == 9


def test_month_is_finished():
    done = [event("1", "2026-11-19T03:00Z", GSW + (1,), NYK + (0,))]
    import datetime as dt
    assert espn.month_is_finished("202611", done, today=dt.date(2026, 12, 1))
    assert not espn.month_is_finished("202611", done, today=dt.date(2026, 11, 30))   # month not over
    assert espn.month_is_finished("202612", done, today=dt.date(2027, 1, 1))        # December -> January
    not_done = done + [event("2", "2026-11-20T00:30Z", LAL, UTA, state="pre", completed=False)]
    assert not espn.month_is_finished("202611", not_done, today=dt.date(2027, 1, 1))


# ---------- The order data.load_schedule() tries its sources in ----------

@pytest.fixture
def sources(monkeypatch, tmp_path):
    """Fake downloads that record which ones were tried, and a throwaway saved-copy file."""
    tried = []
    monkeypatch.setattr(data, "CACHE_FILE", tmp_path / "schedule.json")
    monkeypatch.delenv("VERCEL", raising=False)
    monkeypatch.delenv("CFNBA_SKIP_STATS_NBA", raising=False)

    def fake(name, works):
        def download(season=None):
            tried.append(name)
            if not works:
                raise TimeoutError(f"{name} didn't answer")
            return as_schedule(SAMPLE)
        return download

    def use(nba_works, espn_works):
        monkeypatch.setattr(data, "download_schedule", fake("nba_api", nba_works))
        monkeypatch.setattr(espn, "download_schedule", fake("ESPN", espn_works))
    return tried, use


def test_nba_first_on_your_pc(sources):
    tried, use = sources
    use(nba_works=True, espn_works=True)
    assert data.load_schedule()[1] == "live (nba_api)"
    assert tried == ["nba_api"]


def test_espn_when_nba_fails_and_it_saves_a_copy(sources):
    tried, use = sources
    use(nba_works=False, espn_works=True)
    raw, source = data.load_schedule()
    assert source == "live (ESPN)"
    assert tried == ["nba_api", "ESPN"]
    assert json.loads(data.CACHE_FILE.read_text(encoding="utf-8")) == raw   # ESPN's answer was saved


def test_on_vercel_nba_is_skipped(sources, monkeypatch):
    tried, use = sources
    monkeypatch.setenv("VERCEL", "1")
    use(nba_works=True, espn_works=True)
    assert data.load_schedule()[1] == "live (ESPN)"
    assert tried == ["ESPN"]   # no 30-second wait for NBA.com


def test_saved_copy_then_a_clear_error(sources):
    tried, use = sources
    use(nba_works=False, espn_works=False)
    with pytest.raises(RuntimeError, match="nba_api: TimeoutError; ESPN: TimeoutError"):
        data.load_schedule()
    data.CACHE_FILE.write_text(json.dumps(as_schedule(SAMPLE)), encoding="utf-8")
    assert data.load_schedule()[1].startswith("saved copy (downloads failed: nba_api: TimeoutError")


# ---------- The player-stats snapshot ----------

@pytest.fixture
def player_files(monkeypatch, tmp_path):
    """Point players.py at throwaway files, so tests never touch the real data/ folder."""
    monkeypatch.setattr(players, "CACHE_FILE", tmp_path / "players.json")
    monkeypatch.setattr(players, "SNAPSHOT_FILE", tmp_path / "players_snapshot.json")
    monkeypatch.delenv("VERCEL", raising=False)
    monkeypatch.delenv("CFNBA_SKIP_STATS_NBA", raising=False)
    return tmp_path


def test_snapshot_round_trip(player_files):
    raw = fake_players() | {"saved_at": "2026-11-19T23:40:12Z"}
    players.write_snapshot(raw, players.SNAPSHOT_FILE)
    saved = json.loads(players.SNAPSHOT_FILE.read_text(encoding="utf-8"))
    assert saved["saved_at"] == "2026-11-19T23:40:12Z"
    # Same players and numbers after the round trip, so the MVP model sees no difference.
    assert players.parse_player_stats(saved).equals(players.parse_player_stats(raw))


def test_on_vercel_the_snapshot_is_used_without_asking_nba(player_files, monkeypatch):
    monkeypatch.setenv("VERCEL", "1")

    def must_not_run(*args, **kwargs):
        raise AssertionError("NBA.com must not be asked on Vercel")
    monkeypatch.setattr(players, "download_player_stats", must_not_run)

    with pytest.raises(RuntimeError, match="update_data.py"):   # no snapshot yet: says how to make one
        players.load_player_stats()
    players.write_snapshot(fake_players() | {"saved_at": "2026-11-19T23:40:12Z"}, players.SNAPSHOT_FILE)
    raw, source = players.load_player_stats()
    assert source == "snapshot"
    assert raw["saved_at"] == "2026-11-19T23:40:12Z"


def test_on_your_pc_the_snapshot_is_the_last_resort(player_files, monkeypatch):
    def offline(*args, **kwargs):
        raise ConnectionError("no internet")
    monkeypatch.setattr(players, "download_player_stats", offline)
    players.write_snapshot(fake_players() | {"saved_at": "2026-11-19T23:40:12Z"}, players.SNAPSHOT_FILE)
    assert players.load_player_stats()[1] == "snapshot (download failed: ConnectionError)"
    # A saved copy of this computer's own last download comes before the snapshot.
    players.CACHE_FILE.write_text(json.dumps(fake_players()), encoding="utf-8")
    assert players.load_player_stats()[1] == "saved copy (download failed: ConnectionError)"
