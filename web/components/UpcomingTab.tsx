"use client";

// Tab 2 (Upcoming & picks): games being played right now, then every game left, day by
// day, each drawn as a Matchup row: both teams, each one's chance to win, and a bar
// showing who the model favors (the gold side) and by how much.

import { useMemo, useState } from "react";
import { useApi } from "./SettingsProvider";
import { Heading, Info, LoadingOrError } from "./Table";
import { TeamPicker, Toolbar, type TeamOption } from "./Controls";
import GameDays from "./GameDays";
import Matchup from "./Matchup";
import type { UpcomingGame } from "@/lib/types";

export default function UpcomingTab() {
  // The win chances come from the forecast the Python API already ran (and cached).
  const { data: games, error } = useApi<UpcomingGame[]>("/api/upcoming");
  const [team, setTeam] = useState<string | null>(null); // a team code, or null = all teams

  // Every team that appears in the remaining games, A to Z by name, for the picker.
  // useMemo: only rebuilt when the games change, not on every keystroke in the picker.
  const teams = useMemo<TeamOption[]>(() => {
    const byCode = new Map<string, string>();
    for (const g of games ?? []) {
      byCode.set(g.home, g.home_name);
      byCode.set(g.away, g.away_name);
    }
    return [...byCode].map(([code, name]) => ({ code, name })).sort((a, b) => a.name.localeCompare(b.name));
  }, [games]);

  if (!games) return <LoadingOrError error={error} what="upcoming games" />;

  // Live games get their own panel at the top; the day-by-day list is everything else.
  const live = games.filter((g) => g.status === 2); // 2 = being played right now
  const scheduled = games.filter((g) => g.status !== 2);
  const shown = team === null ? scheduled : scheduled.filter((g) => g.home === team || g.away === team);
  const teamName = teams.find((t) => t.code === team)?.name;

  return (
    <div className="space-y-14">
      {live.length > 0 && (
        // Live games sit in their own red-edged panel: they're the one thing on the page
        // that's changing right now.
        <section aria-labelledby="live-heading" className="rounded-2xl border border-live/30 bg-live/[0.05] px-4 pt-4 pb-1 md:px-5">
          <div className="mb-1 flex items-baseline gap-3">
            <Heading id="live-heading">Live now</Heading>
            <span className="text-sm text-muted">
              {live.length} {live.length === 1 ? "game" : "games"}
            </span>
          </div>
          <ul>
            {live.map((g) => (
              <li key={g.game_id} className="border-b border-live/15 py-3.5 last:border-b-0">
                <Matchup game={g} />
              </li>
            ))}
          </ul>
        </section>
      )}

      <section aria-labelledby="upcoming-heading">
        <Heading id="upcoming-heading" className="mb-5">
          Schedule
        </Heading>
        <Toolbar count={`${shown.length} ${shown.length === 1 ? "game" : "games"} left`}>
          <TeamPicker label="Team" teams={teams} value={team} onChange={setTeam} />
          {/* The key for the bar, said once here instead of in every row. */}
          <p className="flex items-center gap-2 text-sm text-muted">
            <span aria-hidden className="inline-block h-2 w-6 rounded-full bg-pick" />
            Model&apos;s pick
            <span aria-hidden className="ml-2 inline-block h-2 w-6 rounded-full bg-track" />
            Underdog
          </p>
        </Toolbar>
        {/* key={team}: picking another team starts the list over from the first days. */}
        <GameDays
          key={team ?? "all"}
          games={shown}
          gameKey={(g) => g.game_id}
          renderGame={(g) => <Matchup game={g} />}
          empty={<Info>No games left on the schedule{teamName ? ` for the ${teamName}` : ""}.</Info>}
        />
      </section>
    </div>
  );
}
