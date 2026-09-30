import pandas as pd
import pytest

from frank import sample
from frank.model import GamePredictor
from frank.stats import player_season_table, team_season_table

SEASONS = ["2023-24", "2024-25", "2025-26"]


@pytest.fixture(scope="module")
def logs():
    return sample.generate(SEASONS)


def test_team_table(logs):
    tg = logs[0]
    t = team_season_table(tg[tg.SEASON == "2025-26"])
    assert len(t) == 30 and (t["GP"] == 82).all()
    assert t["W"].sum() == t["L"].sum() == 30 * 82 / 2
    assert abs(t["NetRtg"].sum()) < 1  # league-wide net rating is roughly zero


def test_player_table(logs):
    pg = logs[1]
    p = player_season_table(pg[pg.SEASON == "2025-26"], min_games=10)
    assert p["PTS"].is_monotonic_decreasing and (p["GP"] >= 10).all()


def test_model_beats_home_baseline_and_is_calibrated(logs):
    m = GamePredictor().fit(logs[0])
    e = m.evaluate()
    assert e.test_season == "2025-26" and e.n_games == 1230
    assert e.accuracy > e.home_team_accuracy
    r = m.predict("BOS", "LAL")
    assert 0 < r["home_win_prob"] < 1
    # margin and probability must agree on the favorite
    assert (r["margin"] > 0) == (r["home_win_prob"] > 0.5)
    swapped = m.predict("LAL", "BOS")
    assert swapped["margin"] != r["margin"]


def test_no_lookahead(logs):
    """Features for a game must not change if later games are removed."""
    tg = logs[0]
    cut = tg[tg.GAME_DATE < "2025-01-01"]
    a, _ = __import__("frank.model", fromlist=["x"]).build_game_features(tg)
    b, _ = __import__("frank.model", fromlist=["x"]).build_game_features(cut)
    a = a[a.GAME_DATE < "2025-01-01"].set_index("GAME_ID")
    b = b.set_index("GAME_ID")
    pd.testing.assert_frame_equal(a[["ELO_DIFF", "FORM_DIFF", "WIN_PCT_DIFF", "REST_DIFF"]],
                                  b[["ELO_DIFF", "FORM_DIFF", "WIN_PCT_DIFF", "REST_DIFF"]])
