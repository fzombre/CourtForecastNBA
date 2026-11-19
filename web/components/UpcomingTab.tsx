"use client";

// Tab 2 (Upcoming & picks): games being played right now, then every game left with
// the model's predicted winner and how sure it is.

import { useState } from "react";
import { useApi } from "./SettingsProvider";
import Table, { Caption, LoadingOrError, type Column } from "./Table";
import Team from "./Team";
import { pct } from "@/lib/format";
import type { UpcomingGame } from "@/lib/types";

const ALL_TEAMS = "All teams";

/** The predicted winner's full name (the API gives it as a team code). */
function pickName(game: UpcomingGame): string {
  return game.predicted_winner === game.home ? game.home_name : game.away_name;
}

const COLUMNS: Column<UpcomingGame>[] = [
  { header: "Date", cell: (g) => g.date },
  { header: "Type", cell: (g) => g.stage },
  { header: "Away", cell: (g) => <Team code={g.away} name={g.away_name} /> },
  { header: "Home", cell: (g) => <Team code={g.home} name={g.home_name} /> },
  { header: "Predicted winner", cell: (g) => <Team code={g.predicted_winner} name={pickName(g)} /> },
  { header: "Chance", cell: (g) => pct(g.confidence), numeric: true },
];

export default function UpcomingTab() {
  // The win chances come from the forecast the Python API already ran (and cached).
  const { data: games, error } = useApi<UpcomingGame[]>("/api/upcoming");
  const [team, setTeam] = useState(ALL_TEAMS); // the "Team" dropdown

  if (!games) return <LoadingOrError error={error} what="upcoming games" />;

  const live = games.filter((g) => g.status === 2); // 2 = being played right now
  // Every team name that appears in the remaining games, A to Z, for the dropdown.
  const teamNames = [...new Set(games.flatMap((g) => [g.home_name, g.away_name]))].sort();
  const shown = team === ALL_TEAMS ? games : games.filter((g) => g.home_name === team || g.away_name === team);

  return (
    <section>
      {live.length > 0 && (
        <div className="mb-6">
          <h2 className="mb-2 text-xl font-semibold">🔴 Live now</h2>
          <ul className="space-y-1">
            {live.map((g) => (
              <li key={g.game_id} className="flex flex-wrap items-center gap-x-2">
                <Team code={g.away} name={g.away_name} /> {g.away_score} @ <Team code={g.home} name={g.home_name} />{" "}
                {g.home_score} · {g.status_text}
              </li>
            ))}
          </ul>
        </div>
      )}

      <h2 className="mb-2 text-xl font-semibold">Upcoming games</h2>
      <label className="mb-2 flex items-center gap-2 text-sm">
        Team
        <select
          value={team}
          onChange={(event) => setTeam(event.target.value)}
          className="rounded border border-zinc-300 bg-transparent px-2 py-1 dark:border-zinc-700"
        >
          {[ALL_TEAMS, ...teamNames].map((name) => (
            <option key={name}>{name}</option>
          ))}
        </select>
      </label>
      <Caption>{shown.length} games left</Caption>
      <Table columns={COLUMNS} rows={shown} rowKey={(g) => g.game_id} />
    </section>
  );
}
