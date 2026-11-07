"""CourtForecastNBA: the website. Run it with:  streamlit run app.py

Streamlit turns a Python script into a web page. Every time you click
something, Streamlit re-runs this file from top to bottom. To keep that fast,
the slow parts (downloading, simulating) are wrapped in @st.cache_data, which
remembers the result and reuses it instead of redoing the work.
"""
import datetime as dt

import pandas as pd
import streamlit as st

from data import CONFERENCE, add_games_behind, load_schedule, parse_games, standings, team_names
from forecast import build_forecast, expected_wins_by_date

st.set_page_config(page_title="CourtForecastNBA", page_icon="🏀", layout="wide")


# ---------- Load data (cached for 10 minutes) ----------

@st.cache_data(ttl=600, show_spinner="Downloading the NBA schedule...")
def get_games():
    raw, source = load_schedule()
    games, season = parse_games(raw)
    return games, season, source


@st.cache_data(show_spinner="Running the Monte Carlo simulation...")
def get_forecast(games, n_sims):
    return build_forecast(games, n_sims=n_sims, seed=42)


# ---------- Sidebar ----------

st.sidebar.title("🏀 CourtForecastNBA")
n_sims = st.sidebar.select_slider("Simulated seasons", options=[500, 1000, 2000, 5000, 10000], value=2000,
                                  help="More simulations = steadier odds, but slower.")
if st.sidebar.button("🔄 Refresh data"):
    st.cache_data.clear()

try:
    games, season, source = get_games()
except Exception as error:
    st.error(f"Couldn't download the NBA schedule, and there's no saved copy yet.\n\n{error}")
    st.stop()

forecast = get_forecast(games, n_sims)
names = team_names(games)
upcoming = forecast["upcoming"]
odds = forecast["odds"]

st.sidebar.caption(f"Season {season} · data: {source}")
st.sidebar.caption(f"Model trained on {forecast['training_games']} finished games"
                   + ("" if forecast["model"] else " (too few yet, using plain Elo)"))

st.title(f"CourtForecastNBA · {season}")

tabs = st.tabs(["✅ Results", "📅 Upcoming & picks", "📊 Standings",
                "🔮 Predicted standings", "🏆 Playoff odds", "🧠 Model"])


def pct(x):
    return f"{x:.0%}"


# ---------- Tab 1: games already played ----------
with tabs[0]:
    played = games[games["played"]].sort_values("start_utc", ascending=False)
    stage = st.selectbox("Show", ["All"] + sorted(played["stage"].unique()), key="played_stage")
    if stage != "All":
        played = played[played["stage"] == stage]
    st.caption(f"{len(played)} games")
    st.dataframe(pd.DataFrame({
        "Date": played["date"],
        "Type": played["stage"],
        "Away": played["away_name"],
        "Score": played["away_score"].astype(str) + " - " + played["home_score"].astype(str),
        "Home": played["home_name"],
        "Winner": played["winner"].map(names),
    }), hide_index=True, width="stretch")


# ---------- Tab 2: upcoming games with predictions ----------
with tabs[1]:
    live = upcoming[upcoming["status"] == 2]
    if len(live):
        st.subheader("🔴 Live now")
        for game in live.itertuples():
            st.write(f"{game.away_name} {game.away_score} @ {game.home_name} {game.home_score} · {game.status_text}")

    st.subheader("Upcoming games")
    team_filter = st.selectbox("Team", ["All teams"] + sorted(names.values()), key="upcoming_team")
    shown = upcoming
    if team_filter != "All teams":
        shown = upcoming[(upcoming["home_name"] == team_filter) | (upcoming["away_name"] == team_filter)]
    st.caption(f"{len(shown)} games left")
    st.dataframe(pd.DataFrame({
        "Date": shown["date"],
        "Type": shown["stage"],
        "Away": shown["away_name"],
        "Home": shown["home_name"],
        "Predicted winner": shown["predicted_winner"].map(names),
        "Chance": shown["confidence"].map(pct),
    }), hide_index=True, width="stretch")


# ---------- Tab 3: current standings ----------
with tabs[2]:
    table = standings(games)
    left, right = st.columns(2)
    for column, conference in [(left, "East"), (right, "West")]:
        conf = add_games_behind(table[table["conference"] == conference])
        conf.insert(0, "Rank", range(1, len(conf) + 1))
        conf["Team"] = conf["team"].map(names)
        column.subheader(conference)
        column.dataframe(conf[["Rank", "Team", "W", "L", "PCT", "GB"]], hide_index=True,
                         width="stretch", height=565)
    st.caption("Seeds 1-6 make the playoffs, 7-10 go to the play-in tournament.")


# ---------- Tab 4: predicted standings on a future date ----------
with tabs[3]:
    regular_left = upcoming[upcoming["stage"] == "Regular Season"]
    if len(regular_left) == 0:
        st.info("The regular season is over, so the standings are final.")
    else:
        today = dt.date.today()
        last_day = regular_left["date"].max()
        # One option per week (Sundays), plus the last day of the regular season.
        weeks = [today + dt.timedelta(days=d) for d in range(7, (last_day - today).days, 7)]
        options = weeks + [last_day]
        cutoff = st.select_slider("Predicted standings on", options=options, value=options[0],
                                  format_func=lambda d: d.strftime("%b %d, %Y"))
        projected = expected_wins_by_date(games, upcoming, cutoff)
        left, right = st.columns(2)
        for column, conference in [(left, "East"), (right, "West")]:
            conf = projected[projected["conference"] == conference].copy()
            conf.insert(0, "Rank", range(1, len(conf) + 1))
            conf["Team"] = conf["team"].map(names)
            column.subheader(conference)
            column.dataframe(conf[["Rank", "Team", "W", "L"]], hide_index=True,
                             width="stretch", height=565)
        st.caption("Expected record: current wins plus the win chances of every game until that date.")


# ---------- Tab 5: playoff and championship odds ----------
with tabs[4]:
    st.caption(f"Based on {n_sims:,} simulated seasons, including the play-in and every playoff round.")
    board = odds.sort_values("champion", ascending=False).copy()
    board["Team"] = board["team"].map(names)
    top = board.iloc[0]
    st.metric("Title favorite", top["Team"], f"{top['champion']}% to win it all")
    st.dataframe(board.rename(columns={
        "conference": "Conf", "proj_W": "Proj W", "proj_L": "Proj L", "avg_seed": "Avg seed",
        "playoffs": "Playoffs %", "round_2": "2nd round %", "conf_finals": "Conf finals %",
        "finals": "Finals %", "champion": "Title %",
    })[["Team", "Conf", "Proj W", "Proj L", "Avg seed", "Playoffs %", "2nd round %",
        "Conf finals %", "Finals %", "Title %"]], hide_index=True, width="stretch",
        column_config={"Title %": st.column_config.ProgressColumn(format="%.1f%%", min_value=0, max_value=100)})


# ---------- Tab 6: how the model is doing ----------
with tabs[5]:
    accuracy = forecast["accuracy"]
    if accuracy:
        a, b = st.columns(2)
        a.metric("Model picked the winner", pct(accuracy["model"]))
        b.metric("Always picking the home team", pct(accuracy["always_home"]))
        st.caption(f"Tested on the last {accuracy['test_games']} finished games, which the model didn't train on.")
    else:
        st.info("Not enough finished games yet to test the model fairly.")

    model_obj = forecast["model"]
    if model_obj is not None:
        st.subheader("What the model learned")
        st.write("Positive weight = helps the home team. Bigger = matters more per unit.")
        st.dataframe(pd.DataFrame({
            "Feature": ["Elo gap", "Recent margin gap", "Rest days gap"],
            "Weight": model_obj.coef_[0].round(4),
        }), hide_index=True)

    st.subheader("Power ratings (Elo)")
    ratings = pd.DataFrame(forecast["ratings"]).T.reset_index(names="team")
    ratings["Team"] = ratings["team"].map(names)
    ratings["Conf"] = ratings["team"].map(CONFERENCE)
    ratings = ratings.sort_values("elo", ascending=False)
    st.dataframe(ratings[["Team", "Conf", "elo", "margin"]].round(1).rename(
        columns={"elo": "Elo", "margin": "Avg margin (last 10)"}), hide_index=True, width="stretch")
