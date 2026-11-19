"use client";

// Tab 1 (Results): every finished game, newest first, with a filter for the type of game.

import { useState } from "react";
import { useApi } from "./SettingsProvider";
import Table, { Caption, LoadingOrError, type Column } from "./Table";
import type { PlayedGame } from "@/lib/types";

/** The winner's full name. The API gives the winner as a team code, and the game has both names. */
function winnerName(game: PlayedGame): string {
  if (game.winner === game.home) return game.home_name;
  if (game.winner === game.away) return game.away_name;
  return ""; // a tie, which only happens in odd preseason games
}

const COLUMNS: Column<PlayedGame>[] = [
  { header: "Date", cell: (g) => g.date },
  { header: "Type", cell: (g) => g.stage },
  { header: "Away", cell: (g) => g.away_name },
  { header: "Score", cell: (g) => `${g.away_score} - ${g.home_score}`, numeric: true },
  { header: "Home", cell: (g) => g.home_name },
  { header: "Winner", cell: (g) => winnerName(g) },
];

export default function ResultsTab() {
  // Results don't depend on the number of simulations, so the path never changes.
  const { data: games, error } = useApi<PlayedGame[]>("/api/results");
  const [stage, setStage] = useState("All"); // the "Show" dropdown

  if (!games) return <LoadingOrError error={error} what="results" />;

  // The dropdown lists "All" plus every type of game that has been played, A to Z.
  // new Set(...) removes duplicates; [...set] turns it back into a list.
  const stages = ["All", ...[...new Set(games.map((g) => g.stage))].sort()];
  const shown = stage === "All" ? games : games.filter((g) => g.stage === stage);

  return (
    <section>
      <label className="mb-2 flex items-center gap-2 text-sm">
        Show
        <select
          value={stage}
          onChange={(event) => setStage(event.target.value)}
          className="rounded border border-zinc-300 bg-transparent px-2 py-1 dark:border-zinc-700"
        >
          {stages.map((s) => (
            <option key={s}>{s}</option>
          ))}
        </select>
      </label>
      <Caption>{shown.length} games</Caption>
      <Table columns={COLUMNS} rows={shown} rowKey={(g) => g.game_id} />
    </section>
  );
}
