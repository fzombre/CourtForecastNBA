"""Step 3: Monte Carlo simulation of the rest of the season and the playoffs.

The model tells us, for example, "Boston has a 64% chance to win tonight."
But what we want to know is "how many games will Boston win?" and "who wins
the title?". Those depend on dozens of games chained together, which is hard
to work out with a formula.

Monte Carlo is the easy way around that: play the season out with dice.
  - For every remaining game, roll a random number between 0 and 1.
    If it's below the home team's win probability, the home team wins.
  - Add up the wins, seed the conferences, run the play-in and the playoffs
    the same way.
  - Do that thousands of times. If Boston wins the title in 1,800 of 10,000
    simulated seasons, their championship odds are 18%.

The name comes from the Monte Carlo casino: it's all random rolls.
"""
import numpy as np
import pandas as pd

from data import CONFERENCE, EAST, TEAMS, WEST

TEAM_INDEX = {team: i for i, team in enumerate(TEAMS)}


def simulate_regular_season(current_wins, upcoming, n_sims, rng):
    """Returns a (n_sims x 30) array: total regular-season wins per team in each simulation.

    current_wins: array of 30 numbers (wins so far)
    upcoming: DataFrame of remaining regular-season games with a `home_win_prob` column
    """
    wins = np.tile(current_wins, (n_sims, 1)).astype(float)
    if len(upcoming) == 0:
        return wins

    home_idx = upcoming["home"].map(TEAM_INDEX).to_numpy()
    away_idx = upcoming["away"].map(TEAM_INDEX).to_numpy()
    probs = upcoming["home_win_prob"].to_numpy()

    # One random roll per (simulation, game). True = home team won.
    home_won = rng.random((n_sims, len(upcoming))) < probs

    for game in range(len(upcoming)):
        wins[:, home_idx[game]] += home_won[:, game]
        wins[:, away_idx[game]] += ~home_won[:, game]
    return wins


def rank_conference(conference_teams, season_wins, rng):
    """Sort a conference best to worst. Ties are broken by a coin flip.
    (The real NBA tiebreakers are more involved; this is a simple stand-in.)"""
    tiebreak = rng.random(len(conference_teams))
    return sorted(conference_teams,
                  key=lambda t: (season_wins[TEAM_INDEX[t]], tiebreak[conference_teams.index(t)]),
                  reverse=True)


def play_game(home, away, matrix, rng):
    """One game. Returns the winner's team code."""
    p_home = matrix[TEAM_INDEX[home], TEAM_INDEX[away]]
    return home if rng.random() < p_home else away


def play_series(higher_seed, lower_seed, matrix, rng):
    """Best of seven. The higher seed hosts games 1, 2, 5 and 7 (the NBA's 2-2-1-1-1 format)."""
    hosts_higher = [True, True, False, False, True, False, True]
    wins = {higher_seed: 0, lower_seed: 0}
    for higher_at_home in hosts_higher:
        if higher_at_home:
            winner = play_game(higher_seed, lower_seed, matrix, rng)
        else:
            winner = play_game(lower_seed, higher_seed, matrix, rng)
        wins[winner] += 1
        if wins[winner] == 4:
            return winner
    return winner  # never reached: someone always gets to 4 by game 7


def play_in(seeds, matrix, rng):
    """Seeds 7-10 fight for the last two playoff spots. Returns the final 8 seeds."""
    s7, s8, s9, s10 = seeds[6], seeds[7], seeds[8], seeds[9]
    winner_7v8 = play_game(s7, s8, matrix, rng)
    loser_7v8 = s8 if winner_7v8 == s7 else s7
    winner_9v10 = play_game(s9, s10, matrix, rng)
    eighth = play_game(loser_7v8, winner_9v10, matrix, rng)
    return seeds[:6] + [winner_7v8, eighth]


def conference_playoffs(eight_seeds, matrix, rng, results):
    """Runs one conference's bracket and records how far each team got."""
    s = eight_seeds  # s[0] is the 1 seed, s[7] the 8 seed
    for team in s:
        results[team]["playoffs"] += 1

    # Round 1: 1v8, 4v5, 2v7, 3v6 (the lower list index is always the higher seed)
    r1 = [play_series(s[0], s[7], matrix, rng), play_series(s[3], s[4], matrix, rng),
          play_series(s[1], s[6], matrix, rng), play_series(s[2], s[5], matrix, rng)]
    for team in r1:
        results[team]["round_2"] += 1

    # Round 2: (1/8 winner vs 4/5 winner) and (2/7 winner vs 3/6 winner).
    # Higher seed = whoever was seeded better.
    def better_seed_first(a, b):
        return (a, b) if s.index(a) < s.index(b) else (b, a)

    r2 = [play_series(*better_seed_first(r1[0], r1[1]), matrix, rng),
          play_series(*better_seed_first(r1[2], r1[3]), matrix, rng)]
    for team in r2:
        results[team]["conf_finals"] += 1

    champion = play_series(*better_seed_first(r2[0], r2[1]), matrix, rng)
    results[champion]["finals"] += 1
    return champion


def run_monte_carlo(current_wins, upcoming_regular, matrix, n_sims=2000, seed=None):
    """The whole thing: simulate the season + playoffs n_sims times.

    Returns two things:
      - a DataFrame with one row per team: average wins and the % of
        simulations in which they reached each stage;
      - the raw (n_sims x 30) array of final regular-season wins, one row per
        simulated season. The MVP race (mvp.py) reuses it, so a player's team
        record in each of its simulated seasons matches the playoff odds exactly.
    """
    rng = np.random.default_rng(seed)
    season_wins = simulate_regular_season(current_wins, upcoming_regular, n_sims, rng)

    stages = ["playoffs", "round_2", "conf_finals", "finals", "champion"]
    results = {team: {stage: 0 for stage in stages} for team in TEAMS}
    seed_totals = {team: 0 for team in TEAMS}

    for sim in range(n_sims):
        wins = season_wins[sim]
        east = rank_conference(EAST, wins, rng)
        west = rank_conference(WEST, wins, rng)
        for rank, team in enumerate(east + west):
            seed_totals[team] += (rank % 15) + 1

        east_champ = conference_playoffs(play_in(east, matrix, rng), matrix, rng, results)
        west_champ = conference_playoffs(play_in(west, matrix, rng), matrix, rng, results)

        # Finals: home court goes to the team with more regular-season wins.
        if wins[TEAM_INDEX[east_champ]] >= wins[TEAM_INDEX[west_champ]]:
            champion = play_series(east_champ, west_champ, matrix, rng)
        else:
            champion = play_series(west_champ, east_champ, matrix, rng)
        results[champion]["champion"] += 1

    table = pd.DataFrame(results).T
    table = (table / n_sims * 100).round(1)  # counts -> percentages
    table.insert(0, "avg_seed", [round(seed_totals[t] / n_sims, 1) for t in TEAMS])
    table.insert(0, "proj_W", season_wins.mean(axis=0).round(1))
    table.insert(0, "conference", [CONFERENCE[t] for t in TEAMS])
    table.index.name = "team"
    return table.reset_index(), season_wins
