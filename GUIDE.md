# How CourtForecastNBA works: a beginner's guide

This guide walks through the project in the order the data flows:

```
NBA schedule file ──> data.py ──> model.py ──> simulate.py ──> app.py (the website)
   (internet)        table of     win chance    thousands of     tabs you click
                     games        per game      fake seasons
```

---

## 1. Choosing the tools

### Data source: the NBA's own schedule file
`https://cdn.nba.com/static/json/staticData/scheduleLeagueV2.json`

This is the file NBA.com's schedule page reads. It's free, needs no API key, and holds **every game of the
current season**: preseason, regular season, NBA Cup, play-in and playoffs. Finished games have final scores and
upcoming games have their date and teams. It updates through the day, so standings stay current.

Why not the other options?
- **`nba_api` (stats.nba.com):** it's a popular Python library, but the stats site often slows down or blocks
  automated requests, and the requests can hang. The old Frank prototype used it. For game results we don't need
  it at all.
- **Paid APIs (SportsDataIO, Sportradar):** these are reliable, but they cost money and need keys. That's
  overkill for now.
- **balldontlie, ESPN's hidden API:** these work, but they're a third party copying the same data, and they can
  change without warning.

One limit: NBA.com blocks some cloud servers, so the file downloads fine on your own computer but may not on a
hosting service. If it ever fails, the app uses the last copy it saved in `data/schedule.json`.

### Frontend: Streamlit instead of JavaScript
Streamlit turns a Python script into a website. `st.title("Hi")` puts a title on the page and `st.dataframe(table)`
shows a sortable table. Since the backend and the ML are already Python, the whole project stays in one
language. A JavaScript frontend (like React) would mean learning JavaScript, HTML/CSS, a build tool, and how to
send data between a Python server and a browser. That's a good second project, but a lot for a first one.

The tradeoff is that Streamlit sites all look a bit alike, and you have less control over the design. If you
outgrow it later, `data.py`, `model.py` and `simulate.py` stay exactly the same. You'd only replace `app.py`.

---

## 2. `data.py`: getting the games

1. `download_schedule()` downloads the file with `requests.get(...)` and saves a copy to disk.
2. `load_schedule()` tries to download, and falls back to the saved copy if the internet fails.
3. `parse_games()` loops over every game in the JSON and keeps the pieces we care about: date, the two teams,
   scores, and status (1 = not started, 2 = live, 3 = final). Each game becomes one row of a **pandas DataFrame**,
   which works like a spreadsheet inside Python.
4. **Game type:** the third digit of a game id tells you the stage. In `0022600123`, the `2` means regular
   season, `1` means preseason, `4` playoffs, `5` play-in, and `6` the NBA Cup final.
5. `standings()` counts wins and losses from finished **regular-season** games only. Preseason and the Cup
   final don't count toward the real standings.

---

## 3. `model.py`: the machine-learning part

The goal is a number like *"Celtics have a 64% chance to beat the Knicks at home tonight."*

### Step A: describe each game with a few numbers ("features")
For every game we compare the two teams **as they were before tip-off**:

| Feature | Meaning |
|---|---|
| `elo_diff` | Home team's Elo rating minus the away team's |
| `margin_diff` | Home team's average point margin over its last 10 games, minus the away team's |
| `rest_diff` | Home team's days of rest minus the away team's (capped at 3) |

**Elo** is one "strength" number per team. Everyone starts at 1500. After each game the winner takes points from
the loser, and an upset moves more points than an expected win:

```
expected = 1 / (1 + 10 ** (-(home_elo - away_elo + 70) / 400))   # 70 = home-court bonus
change   = 20 * (actual_result - expected)                         # actual_result: 1 home win, 0 loss
```

Say Boston (1600) hosts Detroit (1450). Boston is expected to win about 78% of the time. If Boston wins, it gains
only 20 × 0.22 ≈ 4 points. If Detroit wins, it gains 20 × 0.78 ≈ 16.

### Step B: replay the season (`replay_season`)
We walk through finished games in date order. For each game we write down the features first, then the
result, and only after that do we update Elo and the margins. This order matters a lot. If we updated first, the
model would be peeking at the answer (this mistake is called *data leakage*), and it would look far more accurate
than it really is.

### Step C: train a logistic regression (`train_model`)
Logistic regression is one of the simplest ML models. It learns one weight per feature and squashes the
weighted sum into a probability between 0 and 1:

```
probability = 1 / (1 + e^-(w1*elo_diff + w2*margin_diff + w3*rest_diff + bias))
```

`scikit-learn` finds the weights that best match the real results. The **bias** ends up being the
home-court advantage, because it's what's left when the teams are equal.

**Early-season rule:** with fewer than 300 finished games (roughly the first month), there isn't enough data to
learn the weights reliably. Until then the app uses the plain Elo formula above. The sidebar tells you which
one is active.

### Step D: is it any good? (`backtest_accuracy`)
We train on the first 70% of finished games and test on the last 30%, which the model never saw. The Model tab
compares the model against "always pick the home team." Good NBA models land around 65-70% correct, because
basketball has a lot of randomness.

---

## 4. `simulate.py`: Monte Carlo

The model knows single games, but we want to know who wins the title, and that depends on more than 1,000 games
chained together. Monte Carlo solves this by playing the season with dice:

1. **Regular season:** for each remaining game, pick a random number between 0 and 1. If it's below the home
   team's win chance, the home team wins. Add up the wins.
2. **Seeding:** rank each conference by wins. Ties are broken by a coin flip, which is simpler than the real
   NBA tiebreakers.
3. **Play-in:** 7 hosts 8, and the winner is the 7 seed. 9 hosts 10. The 7/8 loser hosts the 9/10 winner, and
   the winner of that game is the 8 seed.
4. **Playoffs:** 1v8, 4v5, 2v7, 3v6, then the semifinals, the conference finals and the Finals. Every series is
   best of seven, and the better seed hosts games 1, 2, 5 and 7. Playoff games use `matchup_matrix`, a 30×30
   table of "team A at home beats team B" chances from the model.
5. **Repeat** 2,000 times (you can change this in the sidebar). If a team wins in 400 of 2,000 runs, its title
   odds are 20%.

More simulations give steadier numbers, but take longer. With 2,000 runs, a 20% figure can wobble by about ±1%
between runs.

### Predicted standings on a future date
For this one we don't need dice. A team's **expected** wins on a date = wins so far + the sum of its win chances
in every game until then. A 60% game adds 0.6 wins. Averages simply add up, so this is exact and instant.

---

## 5. `forecast.py` and `app.py`

`forecast.py` is a short "glue" file. It runs data → model → simulation in order and returns everything the
website needs.

`app.py` is the website. Three Streamlit ideas cover most of it:
- **The script re-runs on every click.** Streamlit runs `app.py` from top to bottom each time you interact.
- **`@st.cache_data`** remembers the result of slow functions (the download and the simulation), so a click
  doesn't redo them. The download refreshes every 10 minutes, or right away when you press 🔄.
- **`st.tabs`, `st.dataframe`, `st.metric`** are the building blocks. Each tab is one `with tabs[i]:` block.

---

## 6. Honest limitations (and good next steps)

1. **Every team starts at 1500 Elo,** so the first few weeks are close to coin flips with a home-court edge.
   *Next step:* start each team's Elo from last season's final rating (pulled once with `nba_api`).
2. **No injuries, trades or rest days for stars.** The model only sees results.
3. **Playoff games already played aren't locked in yet.** In April the simulator still re-plays the whole
   bracket from the standings. *Next step:* feed real series results into `conference_playoffs`.
4. **Ties use a coin flip, not the NBA's tiebreaker rules.**
5. **More features to try:** back-to-back flags, travel distance, offensive/defensive ratings, and player stats.

To add a feature, follow these steps:
1. Calculate it in `replay_season` (before the Elo update).
2. Add its name to `FEATURES`.
3. Fill it in for upcoming games in `features_for_upcoming` and in `matchup_matrix`.
