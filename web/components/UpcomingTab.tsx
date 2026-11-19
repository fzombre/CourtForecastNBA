"use client";

// Tab 2 (Upcoming & picks): games being played right now, then every game left, day by
// day, each drawn as a Matchup row: both teams, each one's chance to win, and a bar
// showing who the model favors and by how much.

import { useState } from "react";
import { useApi } from "./SettingsProvider";
import { Heading, Info, LoadingOrError } from "./Table";
import { Select, Toolbar } from "./Controls";
import GameDays from "./GameDays";
import Matchup from "./Matchup";
import type { UpcomingGame } from "@/lib/types";

const ALL_TEAMS = "All teams";

export default function UpcomingTab() {
  // The win chances come from the forecast the Python API already ran (and cached).
  const { data: games, error } = useApi<UpcomingGame[]>("/api/upcoming");
  const [team, setTeam] = useState(ALL_TEAMS); // the "Team" dropdown

  if (!games) return <LoadingOrError error={error} what="upcoming games" />;

  // Live games get their own section at the top; the day-by-day list is everything else.
  const live = games.filter((g) => g.status === 2); // 2 = being played right now
  const scheduled = games.filter((g) => g.status !== 2);

  // Every team name that appears in the remaining games, A to Z, for the dropdown.
  const teamNames = [...new Set(games.flatMap((g) => [g.home_name, g.away_name]))].sort();
  const plays = (g: UpcomingGame) => team === ALL_TEAMS || g.home_name === team || g.away_name === team;
  const shown = scheduled.filter(plays);

  return (
    <div className="space-y-12">
      {live.length > 0 && (
        <section aria-labelledby="live-heading">
          <Heading id="live-heading" className="mb-3">
            Live now
          </Heading>
          <ul className="border-t-2 border-live">
            {live.map((g) => (
              <li key={g.game_id} className="border-b border-rule py-3">
                <Matchup game={g} />
              </li>
            ))}
          </ul>
        </section>
      )}

      <section aria-labelledby="upcoming-heading">
        <Heading id="upcoming-heading" className="mb-4">
          Upcoming games
        </Heading>
        <Toolbar count={`${shown.length} ${shown.length === 1 ? "game" : "games"} left`}>
          <Select label="Team" value={team} options={[ALL_TEAMS, ...teamNames]} onChange={setTeam} />
          {/* The key for the bar, said once here instead of in every row. */}
          <p className="flex items-center gap-2 text-sm text-ink-muted">
            <span aria-hidden className="inline-block h-2 w-6 rounded-full bg-paint" />
            Predicted winner&apos;s chance
          </p>
        </Toolbar>
        {/* key={team}: picking another team starts the list over from the first days. */}
        <GameDays
          key={team}
          games={shown}
          gameKey={(g) => g.game_id}
          renderGame={(g) => <Matchup game={g} />}
          empty={<Info>No games left on the schedule{team === ALL_TEAMS ? "" : ` for the ${team}`}.</Info>}
        />
      </section>
    </div>
  );
}
