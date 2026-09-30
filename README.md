# Frank: NBA stats explorer and game predictor

## Run it
```
pip install -r requirements.txt
streamlit run app.py
```
Needs Python 3.10+. The first launch downloads the last four seasons from stats.nba.com (about a minute)
and caches them in `data/`. Use the sidebar button to refresh.

No internet? `FRANK_SAMPLE=1 streamlit run app.py` uses made-up data (real team names, invented results).

## What's in it
- **Teams / Players / Compare players:** sortable stat tables, offense vs defense chart, form trends, game logs.
- **Predict a game:** pick home and away team and rest days. You get win chances, projected margin,
  and a breakdown of which factors drove it.
- **How good is the model?:** it predicts every game of the latest full season using only pre-game
  information, and compares itself to "always pick the home team" and Elo alone.

## How the predictor works
Elo rating (margin-of-victory weighted), 10-game rolling net rating, season win %, rest days and
back-to-backs feed a ridge regression for the home team's margin; win probability comes from that margin.
It does not know about injuries, trades or lineups. Adding those is the obvious next step.

Test with `python -m pytest`.
