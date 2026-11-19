// Grouping helpers for the game lists on the Results and Upcoming tabs.

/**
 * Split a list of games into one group per date, keeping the order they came in.
 *
 *   [{date: "11-18"}, {date: "11-19"}, {date: "11-18"}]
 *     -> [["11-18", [game, game]], ["11-19", [game]]]
 *
 * Days appear in the order their first game appears. The API already sorts the games
 * (newest first for results, soonest first for upcoming), so that's the order we want.
 * A Map (not "compare with the previous game") means a day can never show up twice,
 * even if the API ever sent the games in a different order.
 */
export function groupByDate<Game extends { date: string }>(games: Game[]): [string, Game[]][] {
  const days = new Map<string, Game[]>();
  for (const game of games) {
    const day = days.get(game.date);
    if (day) day.push(game);
    else days.set(game.date, [game]); // a Map remembers the order keys were first added
  }
  return [...days.entries()];
}
