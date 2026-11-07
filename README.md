# CourtForecastNBA

Predicts every remaining game of the 2026-27 NBA season, the standings and the champion.
It uses a machine-learning model for single games and a Monte Carlo simulation for everything after that.

## Run it (Windows, PowerShell)

You need Python 3.10 or newer from [python.org](https://www.python.org/downloads/windows/).
When you install it, tick **"Add python.exe to PATH"**.

Open PowerShell in the folder that holds `CFNBA.tar.gz`, then run:

```powershell
tar -xzf CFNBA.tar.gz              # unzip (tar is built into Windows 10 and 11)
cd CFNBA
python -m venv .venv               # a private box for this project's packages
.\.venv\Scripts\Activate.ps1       # turn the box on; your prompt now starts with (.venv)
pip install -r requirements.txt
streamlit run app.py               # opens http://localhost:8501 in your browser
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
cd CFNBA
.\.venv\Scripts\Activate.ps1
streamlit run app.py
```

Stop the app with **Ctrl + C** in PowerShell.

Run the tests with `pip install pytest` and then `python -m pytest`.

<details><summary>Mac / Linux instead</summary>

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
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

| File | Job |
|---|---|
| `data.py` | Downloads the NBA schedule and turns it into a table of games |
| `model.py` | Elo ratings, features, and the logistic regression that gives win chances |
| `simulate.py` | Monte Carlo: plays out the season, play-in and playoffs thousands of times |
| `forecast.py` | Runs the three steps above in order |
| `app.py` | The Streamlit website |
| `tests/` | Quick checks that run on made-up data |

See **[GUIDE.md](GUIDE.md)** for a plain-language walkthrough of every piece.
