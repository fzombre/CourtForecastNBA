"use client";

// Tab 5 (Playoff odds): each team's chances to make the playoffs, reach each round and
// win the title, from the Monte Carlo simulation in simulate.py.

import { useApi, useSettings } from "./SettingsProvider";
import Table, { Caption, LoadingOrError, type Column } from "./Table";
import type { TeamOdds } from "@/lib/types";

/** A percentage with one decimal, e.g. 20.4 -> "20.4%". The API already sends percentages. */
const percent = (value: number) => `${value.toFixed(1)}%`;

/** A bar that fills up to `value` percent, next to the number (like Streamlit's ProgressColumn). */
function TitleBar({ value }: { value: number }) {
  return (
    <div className="flex items-center justify-end gap-2">
      <div className="h-2 w-24 rounded bg-zinc-200 dark:bg-zinc-800">
        <div className="h-2 rounded bg-orange-500" style={{ width: `${Math.min(100, value)}%` }} />
      </div>
      <span className="w-12">{percent(value)}</span>
    </div>
  );
}

export default function OddsTab() {
  const { sims, teamName } = useSettings();
  const { data: odds, error, loading } = useApi<TeamOdds[]>(`/api/odds?sims=${sims}`);

  // Changing the number of simulations takes a few seconds, so say so instead of showing old numbers silently.
  if (!odds) return <LoadingOrError error={error} what="playoff odds (the simulation takes a few seconds)" />;

  const favorite = odds[0]; // the API sends the teams sorted by title odds, best first

  const columns: Column<TeamOdds>[] = [
    { header: "Team", cell: (t) => teamName(t.team) },
    { header: "Conf", cell: (t) => t.conference },
    { header: "Proj W", cell: (t) => t.proj_W.toFixed(1), numeric: true },
    { header: "Proj L", cell: (t) => t.proj_L.toFixed(1), numeric: true },
    { header: "Avg seed", cell: (t) => t.avg_seed.toFixed(1), numeric: true },
    { header: "Playoffs %", cell: (t) => percent(t.playoffs), numeric: true },
    { header: "2nd round %", cell: (t) => percent(t.round_2), numeric: true },
    { header: "Conf finals %", cell: (t) => percent(t.conf_finals), numeric: true },
    { header: "Finals %", cell: (t) => percent(t.finals), numeric: true },
    { header: "Title %", cell: (t) => <TitleBar value={t.champion} />, numeric: true },
  ];

  return (
    <section>
      <Caption>
        Based on {sims.toLocaleString()} simulated seasons, including the play-in and every playoff round.
        {loading && " Updating..."}
      </Caption>
      {favorite && (
        <div className="mb-4">
          <p className="text-sm text-zinc-500">Title favorite</p>
          <p className="text-2xl font-semibold">{teamName(favorite.team)}</p>
          <p className="text-sm text-green-600">{percent(favorite.champion)} to win it all</p>
        </div>
      )}
      <Table columns={columns} rows={odds} rowKey={(t) => t.team} maxHeight="none" />
    </section>
  );
}
