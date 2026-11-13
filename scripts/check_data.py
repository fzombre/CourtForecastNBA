"""Quick check that the NBA data download works on your computer.

Run it from the project folder with:   py scripts/check_data.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))  # so "import data" finds src/data.py

import data

print(f"Asking nba_api for the {data.current_season()} schedule (can take up to {data.TIMEOUT} seconds)...")
raw = data.download_schedule()          # if this fails, Python prints the reason in red
games, season = data.parse_games(raw)

print(f"OK! Season {season}: {len(games)} games, {games['played'].sum()} finished, "
      f"{(~games['played']).sum()} still to play.")
print()
print("Last 3 finished games:")
print(games[games["played"]].tail(3)[["date", "away", "away_score", "home", "home_score"]].to_string(index=False))
print()
print("Next 3 games:")
print(games[~games["played"]].head(3)[["date", "away", "home"]].to_string(index=False))
print()
print("Top of the standings:")
print(data.standings(games).head(5).to_string(index=False))