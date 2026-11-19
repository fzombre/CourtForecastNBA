# How CourtForecastNBA works: a beginner's guide

This guide walks through the project in the order the data flows:

```
stats.nba.com ──> data.py ──> model.py ──> simulate.py ──> app.py (the website)
 (via nba_api)    table of     win chance    thousands of     tabs you click
                  games        per game      fake seasons
```

All of these files live in `src/`. The tests are in `tests/`, and `scripts/check_data.py` is a quick way to
check that the download works on your computer.

---

## 0. Setting up on Windows: what each command does

The exact commands are in the [README](README.md#run-it-windows-powershell). Here's what they're doing:

- **`python -m venv .venv`** creates a *virtual environment*: a private folder (`.venv`) that holds this project's
  packages, so they don't clash with other Python projects on your PC.
- **`.\.venv\Scripts\Activate.ps1`** switches PowerShell to use that private folder. You'll see `(.venv)` at the
  start of the prompt. You need to run it again in every new PowerShell window. If Windows says *"running scripts
  is disabled"*, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once.
- **`pip install -r requirements.txt`** downloads the libraries listed in `requirements.txt`: Streamlit, pandas,
  NumPy, scikit-learn and nba_api. (`requirements-dev.txt` adds pytest, for running the tests.)
- **`streamlit run src/app.py`** starts a small web server on your PC and opens the site at `http://localhost:8501`.
  "localhost" means "this computer": nobody else can see it. Press Ctrl + C in PowerShell to stop it.
- **`python scripts/check_data.py`** downloads the schedule once and prints a few games and the top of the
  standings. If something's wrong with the download, this shows the error without starting the website.
- **`python -m pytest`** runs the tests in `tests/`. They use a made-up schedule, so they don't need the
  internet. `pyproject.toml` tells pytest that the source code is in `src/`.

If `pip` fails while trying to *build* pandas or numpy, you're probably using a different Python than you think
(for example one that came with MSYS2 or Git tools). Use `py -m pip ...` and `py -m streamlit ...` to make sure
you get the Python from python.org.

The code itself works the same on Windows, Mac and Linux. File paths are built with Python's `pathlib` (which
picks `\` or `/` for you), and the saved data file is always read and written as UTF-8.

---

## 1. Choosing the tools

### Data source: `nba_api` and stats.nba.com
[`nba_api`](https://github.com/swar/nba_api) is a free Python library for the NBA's own stats website,
stats.nba.com. It needs no API key. We use one endpoint, **`scheduleleaguev2`**, which returns **every game of a
season**: preseason, regular season, NBA Cup, play-in and playoffs. Finished games have final scores and upcoming
games have their date and teams. NBA.com updates it as games finish, so the standings stay current.

nba_api also covers player stats, box scores and past seasons, which leaves room to grow (see the next steps at
the end of this guide).

The downside: stats.nba.com is sometimes slow, and it can block automated requests, especially from cloud
servers. So the app protects itself in two ways:
- every request gives up after `TIMEOUT` seconds (30) instead of hanging forever;
- every successful download is saved to `data/schedule.json`, and if a later download fails, the app uses that
  saved copy. The sidebar says whether you're looking at live data or the saved copy.

Why not the other options?
- **The NBA's CDN file** (`cdn.nba.com/.../scheduleLeagueV2.json`): this is the same schedule as a plain file, and
  it's usually faster. The project used it at first, then switched to nba_api so all NBA data comes through
  one library.
- **Paid APIs (SportsDataIO, Sportradar):** these are reliable, but they cost money and need keys. That's
  overkill for now.
- **balldontlie, ESPN's hidden API:** these work, but they're a third party copying the same data, and they can
  change without warning.

### Frontend: Streamlit instead of JavaScript
Streamlit turns a Python script into a website. `st.title("Hi")` puts a title on the page and `st.dataframe(table)`
shows a sortable table. Since the backend and the ML are already Python, the whole project stays in one
language. A JavaScript frontend (like React) would mean learning JavaScript, HTML/CSS, a build tool, and how to
send data between a Python server and a browser. That's a good second project, but a lot for a first one.

The tradeoff is that Streamlit sites all look a bit alike, and you have less control over the design. If you
outgrow it later, `data.py`, `model.py` and `simulate.py` stay exactly the same. You'd only replace `app.py`.

---

## 2. `data.py`: getting the games

1. `current_season()` works out which season to ask for, written the way the NBA writes it: `"2026-27"`. A season
   starts in the fall, so from July on it's this year's season, and before July it's last year's.
2. `download_schedule()` asks stats.nba.com for that season's schedule through nba_api, checks that the answer
   actually contains games, and saves a copy to `data/schedule.json`. You can also ask for an older season,
   for example `download_schedule("2025-26")`.
3. `load_schedule()` tries to download, and falls back to the saved copy if anything goes wrong (no internet, a
   timeout, or NBA.com blocking the request). If there's no saved copy yet, it stops with an error message.
4. `parse_games()` loops over every game in the JSON and keeps the pieces we care about: date, the two teams,
   scores, and status (1 = not started, 2 = live, 3 = final). Each game becomes one row of a **pandas DataFrame**,
   which works like a spreadsheet inside Python.
5. **Game type:** the third digit of a game id tells you the stage. In `0022600123`, the `2` means regular
   season, `1` means preseason, `4` playoffs, `5` play-in, and `6` the NBA Cup final.
6. `standings()` counts wins and losses from finished **regular-season** games only. Preseason and the Cup
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
   *Next step:* start each team's Elo from last season's final rating. `download_schedule("2025-26")` already
   gets last season's games; replay them once and keep the final Elo numbers.
2. **No injuries, trades or rest days for stars.** The model only sees results.
3. **Playoff games already played aren't locked in yet.** In April the simulator still re-plays the whole
   bracket from the standings. *Next step:* feed real series results into `conference_playoffs`.
4. **Ties use a coin flip, not the NBA's tiebreaker rules.**
5. **More features to try:** back-to-back flags, travel distance, offensive/defensive ratings, and player stats.

To add a feature, follow these steps:
1. Calculate it in `replay_season` (before the Elo update).
2. Add its name to `FEATURES`.
3. Fill it in for upcoming games in `features_for_upcoming` and in `matchup_matrix`.
