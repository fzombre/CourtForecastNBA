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
| Model | How accurate the model has been, what it learned, and team power ratings |

## Files

```
src/                 the app's source code
  data.py            downloads the NBA schedule (nba_api) and turns it into a table of games
  model.py           Elo ratings, features, and the logistic regression that gives win chances
  simulate.py        Monte Carlo: plays out the season, play-in and playoffs thousands of times
  forecast.py        runs the three steps above in order
  app.py             the Streamlit website
tests/               quick checks that run on made-up data (no internet needed)
scripts/
  check_data.py      checks that the NBA download works on your computer
data/                the saved copy of the schedule (created on first run, not in git)
requirements.txt     packages the app needs
requirements-dev.txt adds pytest, for running the tests
pyproject.toml       tells pytest where the source code is
```

See **[GUIDE.md](GUIDE.md)** for a plain-language walkthrough of every piece.
