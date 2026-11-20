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

// ---------- /api/mvp: the MVP race ----------

/** One MVP candidate: his stats so far, his place on today's ladder and his chance to win. */
export type MvpCandidate = {
  player_id: number; // NBA.com's id for the player, used for his photo
  name: string; // "Shai Gilgeous-Alexander" (with accents, e.g. "Nikola Jokić")
  team: string; // three-letter code of his current team
  gp: number; // games he has played
  team_gp: number; // games his team has played (the most he could have)
  required: number; // games he must reach to be eligible (65 in an 82-game season)
  can_miss: number; // games he can still miss and stay eligible
  min: number; // minutes per game
  pts: number; // points per game
  reb: number; // rebounds per game
  ast: number; // assists per game
  ts_pct: number; // true shooting %, as a fraction (0.62 = 62%)
  plus_minus: number; // points per game his team outscores opponents by with him on court
  w: number; // his team's wins in the games he played
  l: number; // ... and losses
  win_pct: number; // w / (w + l), as a fraction
  rank: number | null; // place on the "if the season ended today" ladder; null if not on track for the games rule
  today: number; // the model's chance for him on today's stats, in percent (the ladder adds up to 100)
  chance: number; // his chance to win MVP at the end of the season, in percent
  eligible: number; // percent of simulated seasons in which he reaches the required games
  proj_gp: number; // games he's expected to finish the season with
};

/** One of the six numbers the MVP model weighs (mvp.FEATURES in Python). */
export type MvpFeature = "pts" | "reb" | "ast" | "ts_pct" | "plus_minus" | "win_pct";

export type MvpRace = {
  season: string;
  source: string; // where the player stats came from: "live (nba_api)" or "saved copy (...)"
  n_sims: number; // how many seasons were simulated
  games_required: number; // 65
  season_games: number; // 82
  backtest: {
    seasons: number; // past seasons tested, each hidden from training in turn (30)
    top1: number; // seasons in which the model's #1 pick was the real MVP
    top3: number; // seasons in which the real MVP was in the model's top 3
    first_season: string; // "1996-97"
    last_season: string; // "2025-26"
  };
  /** How much each stat moves a player's score, per standard deviation above the average candidate. */
  weights: { feature: MvpFeature; weight: number }[];
  candidates: MvpCandidate[]; // sorted by chance to win, best first
};
