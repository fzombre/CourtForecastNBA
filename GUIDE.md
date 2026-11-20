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

The downside: stats.nba.com is sometimes slow, and it ignores cloud servers completely (we tested it on Vercel:
the request just waits until it times out). So the app protects itself in three ways:
- every request gives up after `TIMEOUT` seconds (30) instead of hanging forever;
- if NBA.com doesn't answer, the schedule comes from **ESPN's public scoreboard** instead (`espn.py`). On a cloud
  host like Vercel the app skips NBA.com and goes straight to ESPN, so it doesn't wait 30 seconds for nothing;
- every successful download is saved to `data/schedule.json`, and if every download fails, the app uses that
  saved copy. The website's "Data" line says which one you're looking at.

**How the ESPN backup works.** ESPN's feed accepts a whole month at a time (`?dates=202611`), so 9 requests cover
a season (October preseason to the June Finals). `espn.py` rewrites each ESPN game in exactly the shape of
NBA.com's schedule file, so `parse_games()` and everything after it can't tell the difference. Only a few things
need translating: six team codes (`GS` → `GSW`, `NY` → `NYK`, `NO` → `NOP`, `SA` → `SAS`, `UTAH` → `UTA`, `WSH` →
`WAS`), ESPN's season types (preseason, regular season, play-in, playoffs), and the NBA Cup final, which ESPN
marks only with a note. When it was added, ESPN's copy of the season matched NBA.com's game for game, with no
score differences. The feed is unofficial, so if ESPN changes it, `espn.py` is the file to fix
(`tests/test_espn.py` checks the translation).

**Player stats have no backup source,** so the deployed site reads `data/players_snapshot.json`, which your PC
downloads (NBA.com does answer home connections) with `python scripts/update_data.py` and pushes to GitHub. The
MVP tab says how old those numbers are. Once a day is plenty, since season averages barely move between games.

Why not the other options?
- **The NBA's CDN file** (`cdn.nba.com/.../scheduleLeagueV2.json`): this is the same schedule as a plain file. The
  project used it at first, then switched to nba_api so all NBA data comes through one library. NBA.com now
  refuses programs on it entirely ("Access Denied", even from home); only images like the team logos still load.
- **Paid APIs (SportsDataIO, Sportradar):** these are reliable, but they cost money and need keys. That's
  overkill for now.
- **balldontlie:** works, but it's a third party copying the same data. ESPN is in the same position, but we only
  use it as a backup.

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

## 5b. `players.py` and `mvp.py`: the MVP race

The MVP race tab (on the Next.js website) answers two questions:
- **The ladder:** if the season ended today, who would win MVP?
- **The prediction:** what is each contender's chance to actually win it in April?

There's no official in-season MVP ranking to download (NBA.com's "MVP Ladder" is a reporter's column, not
data), so the app builds its own from player stats.

### Getting player stats (`players.py`)
`players.py` is `data.py`'s twin for players. It uses nba_api's **`leaguedashplayerstats`** endpoint: one request
returns every player's per-game averages for the season (points, rebounds, assists, shooting, plus/minus, and his
team's record in the games he played). It has the same safety nets as the schedule: a `TIMEOUT`, and a saved copy
in `data/players.json` if a download fails. It also works out **true shooting %**
(`points / (2 × (FGA + 0.44 × FTA))`), the standard measure of how efficiently someone scores.

### Learning how voters pick (`mvp.py`, step 1)
`data/mvp_history.csv` holds every regular's stats from 1996-97 to last season, and who won MVP each year. (It's
built once by `scripts/build_mvp_history.py` and kept in git, so the app never downloads 30 seasons.)

The model gives every candidate a **score**, a weighted sum of six numbers: points, rebounds, assists, true
shooting %, plus/minus and team win %. Then it turns one season's scores into chances that add up to 100%:

```
chance(player) = e^score(player) / (sum of e^score over every candidate that season)
```

This is called a **softmax**. It's the logistic regression from `model.py` stretched from two options (home wins
or away wins) to a whole field of candidates. Training finds the weights that gave the real MVPs the biggest
slices of their seasons. Before training, each stat is **standardized** ("how many standard deviations above the
average candidate"), so points (around 25) and true shooting (around 0.6) are on the same scale and the weights can
be compared. The tab shows them: points and team win % matter most, then plus/minus and assists.

Is it any good? `backtest()` hides one season, trains on the other 29, and checks whom the model picks, for each
of the 30 seasons in turn. It picked the real MVP **16 times** and had him in its **top 3 in 28**. Its misses are
close races that voters decided on the story of the season (Iverson over Shaq in 2001, Embiid over Jokić in 2023).
A stats-only model can't see stories.

### Playing out the rest of the season (`mvp.py`, step 2)
The ladder simply runs today's stats through the model. That's fine in April, but in November it treats 15 games
as the whole season. For the **prediction**, we reuse the 10,000 seasons `simulate.py` already plays for the
playoff odds (so a player's team record matches the odds exactly), and in each one we also play out every
contender's season:

1. **Games played.** Each simulated season draws an availability rate for him (his record so far, blended with
   last season), then the games he plays at that rate. Drawing the *rate* first, instead of flipping a coin for
   each game, copies how injuries really work: one sprain costs 15 games in a row.
2. **The 65-game rule.** Since 2023-24 a player must play 65 games to win MVP. In each simulated season where he
   doesn't reach 65, he gets no chance.
3. **His team's record** comes from that simulated season.
4. **His averages drift.** Hot starts cool off: we estimate his true level by blending this season with last
   season, counted as 15 games' worth. Then his remaining games land randomly around that level.

Then we run the model on every simulated final stat line and average the chances. The two "how sure are we in
November?" settings (the 15 games, and how far averages drift) aren't guesses. `scripts/check_mvp_drift.py`
compares each player's averages on November 20 of the last five seasons with how he actually finished. Counting last
season as 15 games gave the smallest misses, and the drift sizes were tuned so the simulation misses by as much as
reality does.

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
6. **The MVP model only sees box-score numbers,** not storylines, voter fatigue, or advanced stats like
   on/off ratings. The 65-game rule is also simplified: the real rule only counts games of 20+ minutes (with
   two exceptions), and we count every game played. *Next step:* add NBA.com's "Advanced" stats (one more
   request per season in `build_mvp_history.py`) as candidate features and see if the backtest improves.
7. **The MVP history needs a yearly update.** After each MVP is announced, add the winner to `MVP_WINNERS` in
   `src/mvp.py` and run `python scripts/build_mvp_history.py`.

To add a feature, follow these steps:
1. Calculate it in `replay_season` (before the Elo update).
2. Add its name to `FEATURES`.
3. Fill it in for upcoming games in `features_for_upcoming` and in `matchup_matrix`.
