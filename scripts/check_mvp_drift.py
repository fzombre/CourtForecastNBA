"""Checks the two "how sure are we in November?" settings in src/mvp.py against real seasons.

Run it from the project folder with:
    python scripts/check_mvp_drift.py

The MVP prediction plays out the rest of each candidate's season. Two settings decide how
far his averages can still move:
  - PRIOR_SEASON_GAMES: how much last season counts when we estimate his true level
    (hot starts cool off);
  - DRIFT_SD: how widely his final averages can land around that estimate.

This script tests both on the last five seasons. For each one it downloads every
player's averages *as of November 20* (stats.nba.com can cut a season off at any date),
then compares them with how those players really finished (data/mvp_history.csv).

For each stat it prints:
  - the typical miss ("resid sd") when predicting the final average from the November
    one, blending last season in with a few different weights. The weight with the
    smallest miss is the best PRIOR_SEASON_GAMES;
  - the typical miss the simulation *assumes* with the current DRIFT_SD. If it's
    smaller than the real miss, the simulation is too sure of itself: scale DRIFT_SD up
    by (real miss / assumed miss), and the other way round.

It needs the internet (five requests, about 15 seconds).
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import numpy as np  # noqa: E402  (imports after the sys.path line on purpose)
import pandas as pd  # noqa: E402
from nba_api.stats.endpoints import leaguedashplayerstats  # noqa: E402

import mvp  # noqa: E402
from data import TIMEOUT  # noqa: E402
from players import parse_player_stats  # noqa: E402

FIRST_YEARS = [2021, 2022, 2023, 2024, 2025]  # 2021 -> the 2021-22 season
CUTOFF = "11/20"            # month/day the "early" averages stop at, about 15 games in
WEIGHTS_TO_TRY = [0, 15, 30, 60]


def season_name(first_year):
    """2021 -> '2021-22'."""
    return f"{first_year}-{(first_year + 1) % 100:02d}"


def early_stats(first_year):
    """Every player's averages from opening night to November 20 of that season."""
    raw = leaguedashplayerstats.LeagueDashPlayerStats(
        season=season_name(first_year),
        per_mode_detailed="PerGame",
        date_to_nullable=f"{CUTOFF}/{first_year}",
        timeout=TIMEOUT,
    ).get_dict()
    return parse_player_stats(raw)


def main():
    history = mvp.load_history()
    stats = list(mvp.DRIFT_SD)
    rows = []
    for first_year in FIRST_YEARS:
        season, previous = season_name(first_year), season_name(first_year - 1)
        early = early_stats(first_year)
        early = early[(early["min"] >= 28) & (early["gp"] >= 10)]   # likely MVP candidates
        final = history[history["season"] == season].set_index("player_id")
        before = history[history["season"] == previous].set_index("player_id")
        for _, player in early.iterrows():
            pid = player["player_id"]
            # Only players with a final line (50+ games) and a line the season before.
            if pid in final.index and pid in before.index and final.loc[pid, "gp"] >= 50:
                row = {"gp_early": player["gp"], "gp_final": final.loc[pid, "gp"]}
                for stat in stats:
                    row[f"{stat}_early"] = player[stat]
                    row[f"{stat}_final"] = final.loc[pid, stat]
                    row[f"{stat}_before"] = before.loc[pid, stat]
                rows.append(row)
        print(f"{season}: downloaded")
        time.sleep(1.5)  # be polite to stats.nba.com

    d = pd.DataFrame(rows)
    print(f"\n{len(d)} player-seasons compared\n")
    gp = d["gp_early"]
    rest = d["gp_final"] - gp                # games still to come after November 20
    rest_share = rest / d["gp_final"]
    for stat in stats:
        early, final, before = d[f"{stat}_early"], d[f"{stat}_final"], d[f"{stat}_before"]
        misses = []
        for weight in WEIGHTS_TO_TRY:
            level = (gp * early + weight * before) / (gp + weight)            # mvp.true_level()
            predicted = (1 - rest_share) * early + rest_share * level         # mvp.simulate_race()
            misses.append(f"{weight}: {(final - predicted).std():.3f}")
        assumed = (rest_share * mvp.DRIFT_SD[stat]
                   * np.sqrt(1 / (gp + mvp.PRIOR_SEASON_GAMES) + 1 / rest)).mean()
        print(f"{stat:>10}  real miss by weight  {'   '.join(misses)}")
        print(f"{'':>10}  miss the simulation assumes: {assumed:.3f}\n")


if __name__ == "__main__":
    main()
