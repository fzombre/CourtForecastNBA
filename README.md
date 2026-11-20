# CourtForecastNBA

Predicts every remaining game of the 2026-27 NBA season, the standings and the champion.
It uses a machine-learning model for single games and a Monte Carlo simulation for everything after that.

## Run it (Windows, PowerShell)

You need Python 3.10 or newer from [python.org](https://www.python.org/downloads/windows/).
When you install it, tick **"Add python.exe to PATH"**.

Get the code: `git clone https://github.com/fzombre/CourtForecastNBA`, or on GitHub click **Code → Download ZIP**
and extract it. Then open PowerShell in the project folder (the one with `README.md` in it) and run:

```powershell
python -m venv .venv               # a private box for this project's packages
.\.venv\Scripts\Activate.ps1       # turn the box on; your prompt now starts with (.venv)
pip install -r requirements.txt
streamlit run src/app.py           # opens http://localhost:8501 in your browser
```

If `Activate.ps1` fails with *"running scripts is disabled on this system"*, run this once, then activate again:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

That setting only lets your own user account run local scripts like `Activate.ps1`.

If `python` opens the Microsoft Store or says it isn't found, use `py` in place of `python` (for example
`py -m venv .venv`).

**Every time after the first time** you only need these three lines:

```powershell
cd path\to\CourtForecastNBA         # your project folder
.\.venv\Scripts\Activate.ps1
streamlit run src/app.py
```

Stop the app with **Ctrl + C** in PowerShell.

Check that the NBA download works with `python scripts/check_data.py`.

Run the tests with `pip install -r requirements-dev.txt` and then `python -m pytest`.

<details><summary>Mac / Linux instead</summary>

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run src/app.py
```
</details>

## The tabs

| Tab | What it shows |
|---|---|
| Results | Every finished game (preseason, regular season, NBA Cup, play-in, playoffs) and who won |
| Upcoming & picks | Every game left, the predicted winner and how sure the model is |
| Standings | Live East and West standings with games behind |
| Predicted standings | Expected records on any future week, up to the end of the regular season |
| Playoff odds | Each team's chances to make the playoffs, reach each round and win the title |
| MVP race *(Next.js website only)* | Who would win MVP if the season ended today, and each contender's chance to win it |
| Model | How accurate the model has been, what it learned, and team power ratings |

## Files

```
src/                 the app's source code
  data.py            downloads the NBA schedule (nba_api, or ESPN as backup) and turns it into a table of games
  espn.py            the backup schedule source: ESPN's scoreboard, for hosts NBA.com doesn't answer
  model.py           Elo ratings, features, and the logistic regression that gives win chances
  simulate.py        Monte Carlo: plays out the season, play-in and playoffs thousands of times
  forecast.py        runs the three steps above in order
  players.py         downloads every player's per-game averages (nba_api), for the MVP race
  mvp.py             the MVP model (trained on 30 past MVP votes) and the MVP race simulation
  api.py             the web API that the Next.js website in web/ talks to
  app.py             the Streamlit website
tests/               quick checks that run on made-up data (no internet needed)
scripts/
  check_data.py      checks that the NBA download works on your computer
  build_mvp_history.py  rebuilds data/mvp_history.csv (run once a year, after a new MVP is named)
  check_mvp_drift.py    checks the MVP race's "how sure are we in November?" settings on real seasons
  update_data.py     updates data/players_snapshot.json for the deployed site (run daily on your PC)
data/                saved copies of the schedule and player stats (created on first run, not in git),
  mvp_history.csv    plus these two, which are in git: 30 seasons of player stats and who won MVP,
  players_snapshot.json  and the player stats the deployed site reads
requirements.txt     packages the app needs
requirements-dev.txt adds pytest, for running the tests
pyproject.toml       tells pytest where the source code is, and Vercel what the API needs
index.py, vercel.json  how Vercel runs the API (see "Deploying" below)
```

## Deploying (Vercel)

The site is two Vercel projects from this one repo: the Python API (Root Directory `./`, preset FastAPI) and the
website (Root Directory `web`, with the environment variable `API_URL` set to the API's address). Every push to
GitHub redeploys both.

stats.nba.com doesn't answer cloud servers, so the deployed API gets the schedule from ESPN instead (live scores
still work), and player stats for the MVP tab from `data/players_snapshot.json`. Keep that file fresh from your PC,
where NBA.com does answer:

```powershell
python scripts/update_data.py           # download today's player stats into the snapshot; then commit and push it
python scripts/update_data.py --push    # or let it commit and push the snapshot for you
```

Once a day is plenty. The script's own comments explain how to run it automatically with Windows Task Scheduler.

See **[GUIDE.md](GUIDE.md)** for a plain-language walkthrough of every piece.
