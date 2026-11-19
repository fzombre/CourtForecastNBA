// TypeScript descriptions of the JSON that src/api.py sends back.
//
// TypeScript never sees the Python code, so these types are a promise we make by hand:
// "the API will answer with objects shaped like this". Field names match the Python
// column names exactly (so "W" stays "W", and "home_win_prob" stays snake_case).
// If you add or rename a column in api.py, update the matching type here too, and
// `npx tsc --noEmit` will point at every component that needs to change.

/** "East" or "West". A union type: TypeScript rejects any other string. */
export type Conference = "East" | "West";

/** The kinds of games in the schedule (see STAGES in src/data.py). */
export type Stage = "Preseason" | "Regular Season" | "Playoffs" | "Play-In" | "NBA Cup Final" | "Other";

// ---------- /api/overview: the header and the Model tab ----------

/** How the model did on finished games it never trained on (model.backtest_accuracy). */
export type Accuracy = {
  model: number; // share of games the model picked correctly, e.g. 0.66
  always_home: number; // share of games "always pick the home team" got right
  test_games: number; // how many games the test used
};

/** One team's power rating, from the Elo replay in model.py. */
export type Rating = {
  team: string; // three-letter code, e.g. "BOS"
  name: string; // full name, e.g. "Boston Celtics"
  conference: Conference;
  elo: number;
  margin: number; // average point margin over the last 10 games
};

export type Overview = {
  season: string; // e.g. "2026-27"
  source: string; // "live (nba_api)" or "saved copy (...)"
  n_sims: number; // how many seasons the Monte Carlo simulation played (the app's own setting)
  team_names: Record<string, string>; // "BOS" -> "Boston Celtics"
  team_ids: Record<string, number>; // "BOS" -> 1610612738, the NBA id used in logo addresses
  training_games: number; // finished games the model learned from
  using_model: boolean; // false early in the season, when the app uses plain Elo
  weights: number[] | null; // [Elo gap, recent margin gap, rest days gap]; null when using plain Elo
  accuracy: Accuracy | null; // null when there aren't enough finished games to test fairly
  ratings: Rating[]; // sorted best Elo first
};

// ---------- /api/results and /api/upcoming: one object per game ----------

/** The fields every game has, finished or not. */
type GameBase = {
  game_id: string;
  date: string; // US Eastern date as text, "2026-11-18"
  stage: Stage;
  away: string;
  away_name: string;
  away_score: number;
  home: string;
  home_name: string;
  home_score: number;
};

/** A finished game, from /api/results. */
export type PlayedGame = GameBase & {
  winner: string | null; // team code of the winner
};

/** A game that hasn't finished, from /api/upcoming. */
export type UpcomingGame = GameBase & {
  status: 1 | 2; // 1 = not started, 2 = being played right now
  status_text: string; // e.g. "7:30 pm ET" or "4th Qtr"
  home_win_prob: number; // between 0 and 1
  predicted_winner: string; // team code
  confidence: number; // the predicted winner's chance, always 0.5 or more
};

// ---------- /api/standings and /api/projected-standings ----------

/** One row of the current standings table. */
export type StandingsRow = {
  team: string;
  conference: Conference;
  W: number;
  L: number;
  PCT: number; // win percentage as a fraction, e.g. 0.8
  GB: number; // games behind the conference leader
};

/** The whole /api/standings answer: one table per conference. */
export type Standings = Record<Conference, StandingsRow[]>;

/** One row of the predicted standings. W and L are expected values, so they have decimals. */
export type ProjectedRow = {
  team: string;
  conference: Conference;
  W: number;
  L: number;
  PCT: number;
};

export type ProjectedStandings = {
  date: string | null; // the date these standings are for; null once the regular season is over
  date_options: string[]; // every date you can pick, earliest first
  East: ProjectedRow[];
  West: ProjectedRow[];
};

// ---------- /api/odds ----------

/** One team's Monte Carlo results. The odds are percentages (20.4 means 20.4%). */
export type TeamOdds = {
  team: string;
  conference: Conference;
  proj_W: number; // average wins over all simulated seasons
  proj_L: number;
  avg_seed: number;
  playoffs: number;
  round_2: number;
  conf_finals: number;
  finals: number;
  champion: number;
};
