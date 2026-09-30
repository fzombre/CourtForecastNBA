"""Frank: NBA stats explorer and game predictor.

Run with:  streamlit run app.py
Set FRANK_SAMPLE=1 to use made-up offline data instead of stats.nba.com.
"""
from __future__ import annotations

import os

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from frank import data, sample
from frank.model import FEATURE_LABELS, GamePredictor
from frank.stats import player_season_table, team_season_table, with_opponent

N_SEASONS = 4  # the first only warms up Elo ratings; the latest is the model's test season
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]  # categorical slots, in fixed order
FAVORS_HOME, FAVORS_AWAY = "#2a78d6", "#e34948"

st.set_page_config(page_title="Frank · NBA analyzer", page_icon="🏀", layout="wide")


# -- data --------------------------------------------------------------------
@st.cache_data(show_spinner="Loading team game logs…", ttl=6 * 3600)
def load_teams(seasons: tuple[str, ...], use_sample: bool) -> tuple[pd.DataFrame, str | None]:
    if use_sample:
        return sample.generate(list(seasons))[0], "sample"
    try:
        df = data.load_seasons(list(seasons), "T")
        if df.empty:
            raise RuntimeError("stats.nba.com returned no games")
        return df, None
    except Exception as err:  # fall back so the app still works offline
        return sample.generate(list(seasons))[0], str(err)


@st.cache_data(show_spinner="Loading player game logs…", ttl=6 * 3600)
def load_players(season: str, all_seasons: tuple[str, ...], use_sample: bool) -> pd.DataFrame:
    if use_sample:
        pg = sample.generate(list(all_seasons))[1]
        return pg[pg["SEASON"] == season]
    return data.load_seasons([season], "P")


@st.cache_resource(show_spinner="Training the game predictor…")
def train_model(seasons: tuple[str, ...], use_sample: bool) -> GamePredictor:
    team_games, _ = load_teams(seasons, use_sample)
    return GamePredictor().fit(team_games)


def style_fig(fig: go.Figure, height: int = 380) -> go.Figure:
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=30, b=10), hovermode="closest",
                      legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0))
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor="rgba(128,128,128,0.15)", zeroline=False)
    return fig


def pct_cols(df: pd.DataFrame) -> dict:
    return {c: st.column_config.NumberColumn(c, format="%.1f%%") for c in df.columns if c.endswith("%")}


def as_pct(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for c in out.columns:
        if c.endswith("%"):
            out[c] = out[c] * 100
    return out.round({c: 1 for c in out.select_dtypes("float").columns})


# -- sidebar -----------------------------------------------------------------
seasons = tuple(data.recent_seasons(N_SEASONS))
use_sample = os.environ.get("FRANK_SAMPLE") == "1"

with st.sidebar:
    st.title("🏀 Frank")
    st.caption("NBA stats explorer and game predictor")
    team_games, fetch_error = load_teams(seasons, use_sample)
    available = [s for s in seasons if (team_games["SEASON"] == s).any()]
    season = st.selectbox("Season", list(reversed(available)))
    if st.button("Refresh data from NBA.com", disabled=use_sample):
        for s in seasons:
            for kind in ("T", "P"):
                path = data._cache_path(s, kind, "Regular Season")
                if s == data.season_str(data.current_season_start_year()) and path.exists():
                    path.unlink()
        st.cache_data.clear()
        st.cache_resource.clear()
        st.rerun()

using_sample = use_sample or fetch_error is not None
if fetch_error == "sample" or use_sample:
    st.info("Showing made-up sample data (FRANK_SAMPLE=1). Teams are real, players and results are not.")
elif fetch_error:
    st.warning(f"Couldn't reach stats.nba.com, so this is made-up sample data. Details: {fetch_error}")

season_games = team_games[team_games["SEASON"] == season]
teams_tab, players_tab, compare_tab, predict_tab, model_tab = st.tabs(
    ["Teams", "Players", "Compare players", "Predict a game", "How good is the model?"]
)

# -- teams -------------------------------------------------------------------
with teams_tab:
    table = team_season_table(season_games)
    st.subheader(f"Team stats, {season}")
    st.dataframe(as_pct(table), column_config=pct_cols(table), use_container_width=True, height=420,
                 column_order=["Team", "GP", "W", "L", "Win%", "NetRtg", "ORtg", "DRtg", "Pace", "PTS",
                               "Opp PTS", "eFG%", "3P%", "FT%", "REB", "AST", "TOV", "STL", "BLK", "3PM"])
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Offense vs defense** (top right is best)")
        t = table.reset_index()
        fig = px.scatter(t, x="ORtg", y="DRtg", text="Abbr", hover_name="Team",
                         hover_data={"Abbr": False, "Win%": ":.1%", "NetRtg": ":+.1f"})
        fig.update_traces(marker=dict(size=10, color=SERIES[0], line=dict(width=2, color="white")),
                          textposition="top center", textfont=dict(size=10))
        fig.update_yaxes(autorange="reversed", title="Defensive rating (points allowed per 100, lower is better)")
        fig.update_xaxes(title="Offensive rating (points per 100 possessions)")
        st.plotly_chart(style_fig(fig, 460), use_container_width=True)
    with c2:
        st.markdown("**Form through the season** (net rating, 10-game rolling)")
        picks = st.multiselect("Teams", table.index.tolist(), default=table.index[:2].tolist(),
                               max_selections=4, key="team_trend")
        g = with_opponent(season_games)
        g = g[g["TEAM_ABBREVIATION"].isin(picks)].copy()
        g["Rolling net rating"] = g.groupby("TEAM_ABBREVIATION")["NETRTG"].transform(
            lambda s: s.rolling(10, min_periods=3).mean())
        fig = px.line(g, x="GAME_DATE", y="Rolling net rating", color="TEAM_ABBREVIATION",
                      category_orders={"TEAM_ABBREVIATION": picks},
                      color_discrete_sequence=SERIES, labels={"GAME_DATE": "", "TEAM_ABBREVIATION": "Team"})
        fig.update_traces(line=dict(width=2))
        fig.add_hline(y=0, line=dict(color="gray", width=1, dash="dot"))
        fig.update_layout(hovermode="x unified")
        st.plotly_chart(style_fig(fig, 400), use_container_width=True)

# -- players -----------------------------------------------------------------
with players_tab:
    player_games = load_players(season, seasons, using_sample)
    st.subheader(f"Player stats, {season} (per game)")
    f1, f2, f3, f4 = st.columns(4)
    min_gp = f1.number_input("Minimum games", 0, 82, 20)
    min_min = f2.number_input("Minimum minutes per game", 0, 40, 15)
    team_filter = f3.selectbox("Team", ["All"] + sorted(player_games["TEAM_ABBREVIATION"].unique()))
    stat = f4.selectbox("Rank by", ["PTS", "REB", "AST", "STL", "BLK", "3PM", "TS%", "+/-", "MIN"])
    ptable = player_season_table(player_games, min_games=int(min_gp))
    ptable = ptable[ptable["MIN"] >= min_min]
    if team_filter != "All":
        ptable = ptable[ptable["Team"] == team_filter]
    ptable = ptable.sort_values(stat, ascending=False)
    st.dataframe(as_pct(ptable).reset_index(drop=True), column_config=pct_cols(ptable),
                 use_container_width=True, height=380)

    top = ptable.head(15).iloc[::-1]
    fig = px.bar(top, x=stat, y="Player", orientation="h", hover_data=["Team", "GP"],
                 color_discrete_sequence=[SERIES[0]])
    fig.update_traces(marker_line_width=0)
    fig.update_yaxes(title="")
    st.markdown(f"**Top 15 by {stat}**")
    st.plotly_chart(style_fig(fig, 460), use_container_width=True)

    st.markdown("**Game by game**")
    names = ptable.sort_values("PTS", ascending=False)["Player"].tolist()
    if names:
        p1, p2 = st.columns([2, 1])
        who = p1.selectbox("Player", names)
        s2 = p2.selectbox("Stat", ["PTS", "REB", "AST", "FG3M", "MIN", "PLUS_MINUS"])
        log = player_games[player_games["PLAYER_NAME"] == who].sort_values("GAME_DATE").copy()
        log["10-game average"] = log[s2].rolling(10, min_periods=1).mean()
        fig = go.Figure()
        fig.add_bar(x=log["GAME_DATE"], y=log[s2], name=s2, marker_color=SERIES[0], opacity=0.35,
                    customdata=log["MATCHUP"], hovertemplate="%{customdata}<br>%{y}<extra></extra>")
        fig.add_scatter(x=log["GAME_DATE"], y=log["10-game average"], name="10-game average",
                        line=dict(color=SERIES[1], width=2), mode="lines")
        st.plotly_chart(style_fig(fig, 340), use_container_width=True)
        with st.expander("Game log"):
            cols = ["GAME_DATE", "MATCHUP", "WL", "MIN", "PTS", "REB", "AST", "STL", "BLK", "TOV",
                    "FGM", "FGA", "FG3M", "FG3A", "FTM", "FTA", "PLUS_MINUS"]
            st.dataframe(log[cols].iloc[::-1], use_container_width=True, hide_index=True)

# -- compare -----------------------------------------------------------------
with compare_tab:
    st.subheader(f"Compare players, {season}")
    full = player_season_table(player_games, min_games=1)
    options = full.sort_values("PTS", ascending=False)["Player"].tolist()
    chosen = st.multiselect("Pick 2 to 4 players", options, default=options[:2], max_selections=4)
    if len(chosen) >= 2:
        cmp = full[full["Player"].isin(chosen)].set_index("Player").loc[chosen]
        counting = ["PTS", "REB", "AST", "STL", "BLK", "3PM", "TOV"]
        long = cmp[counting].reset_index().melt(id_vars="Player", var_name="Stat", value_name="Per game")
        fig = px.bar(long, x="Stat", y="Per game", color="Player", barmode="group",
                     category_orders={"Player": chosen}, color_discrete_sequence=SERIES)
        fig.update_traces(marker_line_color="rgba(0,0,0,0)", marker_line_width=2)
        st.plotly_chart(style_fig(fig, 400), use_container_width=True)
        st.dataframe(as_pct(cmp).T.round(3), use_container_width=True)
    else:
        st.caption("Pick at least two players.")

# -- predict -----------------------------------------------------------------
with predict_tab:
    model = train_model(seasons, using_sample)
    st.subheader("Predict a game")
    teams = sorted(model.state)
    c1, c2 = st.columns(2)
    home = c1.selectbox("Home team", teams, index=teams.index("BOS") if "BOS" in teams else 0)
    away = c2.selectbox("Away team", teams, index=teams.index("LAL") if "LAL" in teams else 1)
    home_rest = c1.slider("Home team days of rest", 0, 4, 1, help="0 means the second night of a back-to-back")
    away_rest = c2.slider("Away team days of rest", 0, 4, 1)

    if home == away:
        st.caption("Pick two different teams.")
    else:
        r = model.predict(home, away, home_rest, away_rest)
        p = r["home_win_prob"]
        fav, fav_p = (home, p) if p >= 0.5 else (away, 1 - p)
        m1, m2, m3 = st.columns(3)
        m1.metric(f"{home} win chance", f"{p:.0%}")
        m2.metric(f"{away} win chance", f"{1 - p:.0%}")
        m3.metric("Projected margin", f"{fav} by {abs(r['margin']):.1f}")

        st.markdown("**Why:** points each factor adds to the home team's margin, versus an average game")
        contrib = pd.DataFrame({
            "Factor": ["Home court"] + [FEATURE_LABELS[k] for k in r["contributions"]],
            "Points": [r["baseline"]] + list(r["contributions"].values()),
        })
        contrib["Favors"] = contrib["Points"].map(lambda v: home if v >= 0 else away)
        fig = px.bar(contrib.iloc[::-1], x="Points", y="Factor", orientation="h", color="Favors",
                     color_discrete_map={home: FAVORS_HOME, away: FAVORS_AWAY},
                     category_orders={"Favors": [home, away]}, hover_data={"Points": ":+.1f"})
        fig.add_vline(x=0, line=dict(color="gray", width=1))
        fig.update_yaxes(title="")
        st.plotly_chart(style_fig(fig, 320), use_container_width=True)

        h, a = model.state[home], model.state[away]
        st.dataframe(pd.DataFrame({
            home: [f"{h['elo']:.0f}", f"{h['form']:+.1f}", f"{h['win_pct']:.1%}", str(h["last_game"].date())],
            away: [f"{a['elo']:.0f}", f"{a['form']:+.1f}", f"{a['win_pct']:.1%}", str(a["last_game"].date())],
        }, index=["Elo rating", "Recent net rating", f"Win % ({h['season']})", "Last game"]),
            use_container_width=True)
        st.caption("Ratings are as of each team's latest game in the data. Before a new season starts "
                   "they reflect last season, so trades and injuries aren't accounted for.")

    st.markdown("**Power rankings (Elo)**")
    pr = model.power_rankings()
    pr["Win%"] = pr["Win%"] * 100
    pr.index = pr.index + 1
    st.dataframe(pr.round(1), column_config={"Win%": st.column_config.NumberColumn(format="%.1f%%")},
                 use_container_width=True, height=400)

# -- model -------------------------------------------------------------------
with model_tab:
    ev = model.evaluate()
    st.subheader(f"Tested on every {ev.test_season} game it never saw")
    st.caption(f"The model trained on {', '.join(s for s in seasons[1:] if s < ev.test_season)} and predicted "
               f"all {ev.n_games} games of {ev.test_season} one at a time, using only information "
               "available before each tip-off.")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Picked the winner", f"{ev.accuracy:.1%}")
    k2.metric("Always pick home team", f"{ev.home_team_accuracy:.1%}")
    k3.metric("Elo alone", f"{ev.elo_accuracy:.1%}")
    k4.metric("Average margin error", f"{ev.margin_mae:.1f} pts")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Calibration:** when it says 70%, does the home team win about 70% of the time?")
        cal = ev.calibration
        fig = go.Figure()
        fig.add_scatter(x=[0, 1], y=[0, 1], mode="lines", name="Perfect",
                        line=dict(color="gray", width=1, dash="dot"))
        fig.add_scatter(x=cal["predicted"], y=cal["actual"], mode="lines+markers", name="Model",
                        line=dict(color=SERIES[0], width=2), marker=dict(size=9),
                        customdata=cal["games"],
                        hovertemplate="Predicted %{x:.0%}<br>Actual %{y:.0%}<br>%{customdata} games<extra></extra>")
        fig.update_xaxes(title="Predicted home win chance", tickformat=".0%", range=[0, 1])
        fig.update_yaxes(title="Actual home win rate", tickformat=".0%", range=[0, 1])
        st.plotly_chart(style_fig(fig, 380), use_container_width=True)
    with c2:
        st.markdown(f"**Brier score** {ev.brier:.3f} (lower is better, 0.25 is a coin flip) · "
                    f"**Log loss** {ev.log_loss:.3f}")
        preds = ev.predictions.sort_values("GAME_DATE", ascending=False).copy()
        preds["Result"] = preds["CORRECT"].map({True: "✓ right", False: "✗ wrong"})
        preds["HOME_WIN_PROB"] = preds["HOME_WIN_PROB"] * 100
        st.dataframe(
            preds[["GAME_DATE", "HOME", "AWAY", "HOME_PTS", "AWAY_PTS", "HOME_WIN_PROB", "PRED_MARGIN", "Result"]],
            column_config={"GAME_DATE": st.column_config.DateColumn("Date"),
                           "HOME_WIN_PROB": st.column_config.NumberColumn("Home win %", format="%.0f%%"),
                           "PRED_MARGIN": st.column_config.NumberColumn("Pred. margin", format="%+.1f")},
            use_container_width=True, hide_index=True, height=380)
