// TypeScript descriptions of the JSON that src/api.py sends back.
// Field names match the Python column names exactly, so "W" stays "W".

/** One row of the standings table, from /api/standings. */
export type StandingsRow = {
  team: string; // three-letter code, e.g. "BOS"
  conference: "East" | "West";
  W: number;
  L: number;
  PCT: number; // win percentage as a fraction, e.g. 0.8
  GB: number; // games behind the conference leader
};

/** The whole /api/standings answer: one table per conference. */
export type Standings = Record<"East" | "West", StandingsRow[]>;
