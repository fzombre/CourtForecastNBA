"""Season summaries built from game logs."""
from __future__ import annotations

import pandas as pd


def possessions(df: pd.DataFrame) -> pd.Series:
    """Standard box-score possession estimate."""
    return df["FGA"] + 0.44 * df["FTA"] - df["OREB"] + df["TOV"]


def with_opponent(team_games: pd.DataFrame) -> pd.DataFrame:
    """Attach each team-game's opponent box score as OPP_* columns."""
    cols = ["GAME_ID", "TEAM_ABBREVIATION", "PTS", "FGA", "FTA", "OREB", "DREB", "TOV", "FGM", "FG3M"]
    opp = team_games[cols].rename(columns={c: f"OPP_{c}" for c in cols if c != "GAME_ID"})
    df = team_games.merge(opp, on="GAME_ID")
    df = df[df["TEAM_ABBREVIATION"] != df["OPP_TEAM_ABBREVIATION"]].copy()
    df["POSS"] = possessions(df)
    df["OPP_POSS"] = df["OPP_FGA"] + 0.44 * df["OPP_FTA"] - df["OPP_OREB"] + df["OPP_TOV"]
    df["GAME_POSS"] = (df["POSS"] + df["OPP_POSS"]) / 2
    df["ORTG"] = 100 * df["PTS"] / df["GAME_POSS"]
    df["DRTG"] = 100 * df["OPP_PTS"] / df["GAME_POSS"]
    df["NETRTG"] = df["ORTG"] - df["DRTG"]
    df["IS_HOME"] = df["MATCHUP"].str.contains(" vs. ")
    return df.sort_values(["GAME_DATE", "GAME_ID"]).reset_index(drop=True)


def team_season_table(team_games: pd.DataFrame) -> pd.DataFrame:
    """One row per team: record, per-game averages, and efficiency ratings."""
    df = with_opponent(team_games)
    g = df.groupby("TEAM_ABBREVIATION")
    out = pd.DataFrame({
        "Team": g["TEAM_NAME"].first(),
        "GP": g.size(),
        "W": g["WL"].apply(lambda s: (s == "W").sum()),
    })
    out["L"] = out["GP"] - out["W"]
    out["Win%"] = out["W"] / out["GP"]
    out["PTS"] = g["PTS"].mean()
    out["Opp PTS"] = g["OPP_PTS"].mean()
    out["Margin"] = out["PTS"] - out["Opp PTS"]
    tot = g[["PTS", "OPP_PTS", "GAME_POSS", "FGM", "FGA", "FG3M", "FG3A", "FTM", "FTA"]].sum()
    out["ORtg"] = 100 * tot["PTS"] / tot["GAME_POSS"]
    out["DRtg"] = 100 * tot["OPP_PTS"] / tot["GAME_POSS"]
    out["NetRtg"] = out["ORtg"] - out["DRtg"]
    out["Pace"] = g["GAME_POSS"].mean()
    out["FG%"] = tot["FGM"] / tot["FGA"]
    out["3P%"] = tot["FG3M"] / tot["FG3A"]
    out["FT%"] = tot["FTM"] / tot["FTA"]
    out["eFG%"] = (tot["FGM"] + 0.5 * tot["FG3M"]) / tot["FGA"]
    for col in ("REB", "AST", "TOV", "STL", "BLK", "FG3M"):
        out[col] = g[col].mean()
    out = out.rename(columns={"FG3M": "3PM"})
    out.index.name = "Abbr"
    return out.sort_values("Win%", ascending=False)


PLAYER_STATS = ["MIN", "PTS", "REB", "AST", "STL", "BLK", "TOV", "FG3M", "PLUS_MINUS"]


def player_season_table(player_games: pd.DataFrame, min_games: int = 1) -> pd.DataFrame:
    """Per-game averages and shooting splits per player."""
    df = player_games.copy()
    g = df.groupby("PLAYER_ID")
    out = pd.DataFrame({
        "Player": g["PLAYER_NAME"].last(),
        "Team": g["TEAM_ABBREVIATION"].last(),  # most recent team if traded
        "GP": g.size(),
    })
    out = out.join(g[PLAYER_STATS].mean())
    tot = g[["FGM", "FGA", "FG3M", "FG3A", "FTM", "FTA", "PTS"]].sum()
    out["FG%"] = tot["FGM"] / tot["FGA"].where(tot["FGA"] > 0)
    out["3P%"] = tot["FG3M"] / tot["FG3A"].where(tot["FG3A"] > 0)
    out["FT%"] = tot["FTM"] / tot["FTA"].where(tot["FTA"] > 0)
    tsa = 2 * (tot["FGA"] + 0.44 * tot["FTA"])
    out["TS%"] = tot["PTS"] / tsa.where(tsa > 0)
    out = out.rename(columns={"FG3M": "3PM", "PLUS_MINUS": "+/-"})
    out = out[out["GP"] >= min_games]
    return out.sort_values("PTS", ascending=False)
