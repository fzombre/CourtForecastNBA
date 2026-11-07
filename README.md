# CourtForecastNBA

Predicts every remaining game of the 2026-27 NBA season, the standings and the champion.
It uses a machine-learning model for single games and a Monte Carlo simulation for everything after that.

## Run it

You need Python 3.10 or newer.

```bash
cd CFNBA
python -m venv .venv              # a private box for this project's packages
source .venv/bin/activate         # on Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py              # opens http://localhost:8501 in your browser
```

Run the tests with `pip install pytest` and then `python -m pytest`.

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
