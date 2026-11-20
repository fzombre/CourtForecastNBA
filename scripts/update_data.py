"""Updates the player-stats snapshot the deployed website reads (data/players_snapshot.json).

Why: the deployed API runs on Vercel, and stats.nba.com doesn't answer cloud servers. The
schedule has a second source there (ESPN, src/espn.py), but player stats don't, so your
PC downloads them (NBA.com does answer home connections) and the snapshot travels to
Vercel with the code. See src/players.py.

Run it from the project folder:

    python scripts/update_data.py           # download and save the snapshot; you commit and push
    python scripts/update_data.py --push    # same, then commit and push just that file for you

Every push to GitHub makes Vercel redeploy, so a minute or two later the MVP tab shows
the new numbers. Once a day is plenty: season averages barely move between games.

To run it every day by itself (Windows Task Scheduler):
    Create Basic Task -> Daily, e.g. 9:00 AM -> Start a program:
        Program:   the full path of python.exe (run `where python` to see it)
        Arguments: scripts\\update_data.py --push
        Start in:  this project's folder
The PC has to be on (and git signed in to GitHub) at that time; if it was off, Task
Scheduler runs it the next time you start the PC if you tick "Run task as soon as
possible after a scheduled start is missed" in the task's settings.
"""
import argparse
import subprocess
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT / "src"))  # so we can import the app's own modules

from players import SNAPSHOT_FILE, download_player_stats, write_snapshot  # noqa: E402

RETRIES = 3  # NBA.com sometimes times out once; try again before giving up


def git(*args):
    """Run a git command in the project folder; stop with its message if it fails."""
    result = subprocess.run(["git", "-C", str(PROJECT), *args], capture_output=True, text=True)
    if result.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} failed:\n{result.stderr.strip() or result.stdout.strip()}")
    return result.stdout


def download():
    """Player stats from NBA.com, trying up to RETRIES times."""
    for attempt in range(1, RETRIES + 1):
        try:
            return download_player_stats()
        except Exception as error:
            print(f"Download attempt {attempt} failed: {type(error).__name__}: {error}")
    raise SystemExit("Couldn't download player stats from NBA.com. Check your internet connection and try again.")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--push", action="store_true",
                        help="also commit data/players_snapshot.json and push it to GitHub")
    args = parser.parse_args()

    raw = download()
    write_snapshot(raw)
    players = len(raw["resultSets"][0]["rowSet"])
    relative = SNAPSHOT_FILE.relative_to(PROJECT).as_posix()   # "data/players_snapshot.json"
    print(f"Saved {players} players to {relative} (stats as of {raw['saved_at']} UTC)")

    if not args.push:
        print(f"Next: commit and push {relative} (git add {relative}; git commit; git push)")
        return

    # Commit only the snapshot, never anything else you happen to be working on.
    if not git("status", "--porcelain", "--", relative).strip():
        print("The snapshot didn't change since the last commit: nothing to push.")
        return
    git("add", "--", relative)
    git("commit", "-m", f"Update player stats snapshot ({raw['saved_at'][:10]})", "--", relative)
    git("push")
    print("Pushed. Vercel will redeploy with the new numbers in a minute or two.")


if __name__ == "__main__":
    main()
