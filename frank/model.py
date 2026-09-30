"""Game outcome predictor.

Each game is described by the difference between the two teams going into it:
  - Elo rating (updated after every game, weighted by margin of victory)
  - recent form: exponentially weighted net rating over roughly the last 10 games
  - season-to-date win percentage
  - days of rest, and whether either team is on the second night of a back-to-back

A ridge regression predicts the home team's margin. The win probability comes from
that margin and the spread of past errors, so the two numbers always agree.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.stats import norm
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .stats import with_opponent

ELO_START = 1500.0
ELO_K = 20.0
ELO_HOME = 100.0
ELO_CARRYOVER = 0.75  # share of a team's Elo kept between seasons
FORM_SPAN = 10
MAX_REST = 4

FEATURES = ["ELO_DIFF", "FORM_DIFF", "WIN_PCT_DIFF", "REST_DIFF", "HOME_B2B", "AWAY_B2B"]
FEATURE_LABELS = {
    "ELO_DIFF": "Elo rating gap",
    "FORM_DIFF": "Recent net rating gap",
    "WIN_PCT_DIFF": "Season win % gap",
    "REST_DIFF": "Rest days gap",
    "HOME_B2B": "Home team on a back-to-back",
    "AWAY_B2B": "Away team on a back-to-back",
}


def _mov_multiplier(margin: float, winner_elo_diff: float) -> float:
    return ((abs(margin) + 3) ** 0.8) / (7.5 + 0.006 * winner_elo_diff)


def compute_elo(games: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, float]]:
    """Add pre-game HOME_ELO / AWAY_ELO to a home-vs-away games frame; also return final ratings."""
    elo: dict[str, float] = {}
    season_of: dict[str, str] = {}
    home_pre, away_pre = [], []
    for row in games.itertuples(index=False):
        for team in (row.HOME, row.AWAY):
            if team not in elo:
                elo[team] = ELO_START
            elif season_of[team] != row.SEASON:
                elo[team] = ELO_CARRYOVER * elo[team] + (1 - ELO_CARRYOVER) * ELO_START
            season_of[team] = row.SEASON
        h, a = elo[row.HOME], elo[row.AWAY]
        home_pre.append(h)
        away_pre.append(a)
        exp_home = 1 / (1 + 10 ** (-(h + ELO_HOME - a) / 400))
        winner_diff = (h + ELO_HOME - a) if row.MARGIN > 0 else (a - h - ELO_HOME)
        shift = ELO_K * _mov_multiplier(row.MARGIN, winner_diff) * (row.HOME_WIN - exp_home)
        elo[row.HOME] = h + shift
        elo[row.AWAY] = a - shift
    out = games.copy()
    out["HOME_ELO"] = home_pre
    out["AWAY_ELO"] = away_pre
    return out, elo


def team_form(team_games: pd.DataFrame) -> pd.DataFrame:
    """Per team-game, what was known before tip-off (PRE_*) and right after (POST_*)."""
    df = with_opponent(team_games)
    df = df.sort_values(["TEAM_ABBREVIATION", "GAME_DATE", "GAME_ID"])
    by_team = df.groupby("TEAM_ABBREVIATION", group_keys=False)
    df["POST_FORM"] = by_team["NETRTG"].transform(lambda s: s.ewm(span=FORM_SPAN).mean())
    df["PRE_FORM"] = by_team["POST_FORM"].shift(1).fillna(0.0)

    df["WIN"] = (df["WL"] == "W").astype(float)
    by_ts = df.groupby(["TEAM_ABBREVIATION", "SEASON"], group_keys=False)
    df["POST_WIN_PCT"] = by_ts["WIN"].transform(lambda s: s.expanding().mean())
    df["PRE_WIN_PCT"] = by_ts["POST_WIN_PCT"].shift(1).fillna(0.5)

    prev_date = by_ts["GAME_DATE"].shift(1)
    rest = (df["GAME_DATE"] - prev_date).dt.days - 1
    df["REST"] = rest.fillna(MAX_REST).clip(0, MAX_REST)
    return df


def build_game_features(team_games: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """One row per game with FEATURES and targets, plus each team's latest state for predictions."""
    from .data import team_games_to_matchups

    games, elo_now = compute_elo(team_games_to_matchups(team_games))
    form = team_form(team_games)
    keep = ["GAME_ID", "TEAM_ABBREVIATION", "PRE_FORM", "PRE_WIN_PCT", "REST"]
    home = form[keep].rename(columns=lambda c: f"H_{c}" if c != "GAME_ID" else c)
    away = form[keep].rename(columns=lambda c: f"A_{c}" if c != "GAME_ID" else c)
    games = games.merge(home, left_on=["GAME_ID", "HOME"], right_on=["GAME_ID", "H_TEAM_ABBREVIATION"])
    games = games.merge(away, left_on=["GAME_ID", "AWAY"], right_on=["GAME_ID", "A_TEAM_ABBREVIATION"])
    games = _feature_columns(games, games["HOME_ELO"], games["AWAY_ELO"], games["H_PRE_FORM"],
                             games["A_PRE_FORM"], games["H_PRE_WIN_PCT"], games["A_PRE_WIN_PCT"],
                             games["H_REST"], games["A_REST"])
    games = games.sort_values(["GAME_DATE", "GAME_ID"]).reset_index(drop=True)

    last = form.sort_values(["GAME_DATE", "GAME_ID"]).groupby("TEAM_ABBREVIATION").tail(1)
    state = {
        r.TEAM_ABBREVIATION: {
            "elo": elo_now[r.TEAM_ABBREVIATION], "form": r.POST_FORM, "win_pct": r.POST_WIN_PCT,
            "last_game": r.GAME_DATE, "season": r.SEASON, "team_name": r.TEAM_NAME,
        }
        for r in last.itertuples(index=False)
    }
    return games, state


def _feature_columns(df, h_elo, a_elo, h_form, a_form, h_wp, a_wp, h_rest, a_rest):
    df = df.copy()
    df["ELO_DIFF"] = h_elo - a_elo
    df["FORM_DIFF"] = h_form - a_form
    df["WIN_PCT_DIFF"] = h_wp - a_wp
    df["REST_DIFF"] = h_rest - a_rest
    df["HOME_B2B"] = (h_rest == 0).astype(float)
    df["AWAY_B2B"] = (a_rest == 0).astype(float)
    return df


@dataclass
class Evaluation:
    test_season: str
    n_games: int
    accuracy: float
    brier: float
    log_loss: float
    margin_mae: float
    home_team_accuracy: float
    elo_accuracy: float
    calibration: pd.DataFrame
    predictions: pd.DataFrame


class GamePredictor:
    def __init__(self, alpha: float = 1.0):
        self.alpha = alpha
        self.pipeline = None
        self.sigma = 12.0
        self.state: dict = {}
        self.games: pd.DataFrame | None = None

    # -- training -----------------------------------------------------------
    @staticmethod
    def _trainable(games: pd.DataFrame) -> pd.DataFrame:
        # The first loaded season only warms up the ratings; everyone starts at the same Elo.
        first = games["SEASON"].min()
        return games[games["SEASON"] != first]

    def _fit_rows(self, rows: pd.DataFrame) -> None:
        self.pipeline = make_pipeline(StandardScaler(), Ridge(alpha=self.alpha))
        self.pipeline.fit(rows[FEATURES], rows["MARGIN"])
        resid = rows["MARGIN"] - self.pipeline.predict(rows[FEATURES])
        self.sigma = float(resid.std())

    def fit(self, team_games: pd.DataFrame) -> "GamePredictor":
        self.games, self.state = build_game_features(team_games)
        rows = self._trainable(self.games)
        if len(rows) < 100:
            raise ValueError("Need at least two seasons of games to train the predictor.")
        self._fit_rows(rows)
        return self

    def evaluate(self) -> Evaluation:
        """Train on every season but the latest, then score the latest season game by game."""
        rows = self._trainable(self.games)
        counts = rows["SEASON"].value_counts()
        # A season that has only just tipped off is too small to judge the model on.
        full = counts[counts >= 200].index
        test_season = full.max() if len(full) else rows["SEASON"].max()
        train, test = rows[rows["SEASON"] < test_season], rows[rows["SEASON"] == test_season]
        if train.empty or test.empty:
            raise ValueError("Need at least three seasons of games to evaluate on a held-out season.")
        holdout = GamePredictor(self.alpha)
        holdout._fit_rows(train)
        margin = holdout.pipeline.predict(test[FEATURES])
        p = norm.cdf(margin / holdout.sigma)
        y = test["HOME_WIN"].to_numpy()
        eps = 1e-9
        elo_p = 1 / (1 + 10 ** (-(test["ELO_DIFF"] + ELO_HOME) / 400))
        preds = test[["GAME_DATE", "HOME", "AWAY", "HOME_PTS", "AWAY_PTS", "MARGIN"]].copy()
        preds["PRED_MARGIN"] = margin
        preds["HOME_WIN_PROB"] = p
        preds["CORRECT"] = (p > 0.5) == (y == 1)
        bins = pd.cut(preds["HOME_WIN_PROB"], np.linspace(0, 1, 11), include_lowest=True)
        calib = preds.assign(WIN=y).groupby(bins, observed=True).agg(
            predicted=("HOME_WIN_PROB", "mean"), actual=("WIN", "mean"), games=("WIN", "size")
        ).reset_index(drop=True)
        return Evaluation(
            test_season=test_season,
            n_games=len(test),
            accuracy=float(preds["CORRECT"].mean()),
            brier=float(np.mean((p - y) ** 2)),
            log_loss=float(-np.mean(y * np.log(p + eps) + (1 - y) * np.log(1 - p + eps))),
            margin_mae=float(np.mean(np.abs(margin - test["MARGIN"]))),
            home_team_accuracy=float(y.mean()),
            elo_accuracy=float(np.mean((elo_p > 0.5) == (y == 1))),
            calibration=calib,
            predictions=preds,
        )

    # -- prediction ---------------------------------------------------------
    def predict(self, home: str, away: str, home_rest: int = 1, away_rest: int = 1) -> dict:
        if self.pipeline is None:
            raise RuntimeError("Call fit() first.")
        h, a = self.state[home], self.state[away]
        vals = [h["elo"], a["elo"], h["form"], a["form"], h["win_pct"], a["win_pct"],
                min(home_rest, MAX_REST), min(away_rest, MAX_REST)]
        row = _feature_columns(pd.DataFrame(index=[0]), *(pd.Series([float(v)]) for v in vals))
        margin = float(self.pipeline.predict(row[FEATURES])[0])
        contributions = self.contributions(row)
        return {
            "home": home, "away": away,
            "home_win_prob": float(norm.cdf(margin / self.sigma)),
            "margin": margin,
            "features": row[FEATURES].iloc[0].to_dict(),
            "contributions": contributions,
            "baseline": float(self.pipeline[-1].intercept_),
        }

    def contributions(self, row: pd.DataFrame) -> dict[str, float]:
        """How many points of predicted margin each feature adds, relative to an average game."""
        scaler, ridge = self.pipeline[0], self.pipeline[-1]
        z = (row[FEATURES].to_numpy()[0] - scaler.mean_) / scaler.scale_
        return {f: float(c) for f, c in zip(FEATURES, z * ridge.coef_)}

    def power_rankings(self) -> pd.DataFrame:
        rows = [{"Team": k, "Name": v["team_name"], "Elo": v["elo"], "Recent net rtg": v["form"],
                 "Win%": v["win_pct"], "Last game": v["last_game"].date()} for k, v in self.state.items()]
        return pd.DataFrame(rows).sort_values("Elo", ascending=False).reset_index(drop=True)
