"use client";

// Tab 4 (Predicted standings): expected records on a future date, picked with a slider.
// The math (current wins + the win chances of every game until that date) runs in
// Python: forecast.expected_wins_by_date(). This component only draws the result.

import { useState } from "react";
import { useApi } from "./SettingsProvider";
import Table, { Caption, Info, LoadingOrError, type Column } from "./Table";
import Team from "./Team";
import { longDate } from "@/lib/format";
import type { ProjectedRow, ProjectedStandings } from "@/lib/types";

export default function PredictedTab() {
  // The date picked on the slider. null = "none picked yet", which makes the API choose
  // the first option (a week from today) and send us the list of all options.
  const [date, setDate] = useState<string | null>(null);

  const path = "/api/projected-standings" + (date ? `?date=${date}` : "");
  const { data, error, loading } = useApi<ProjectedStandings>(path);

  if (!data) return <LoadingOrError error={error} what="predicted standings" />;
  if (data.date === null) return <Info>The regular season is over, so the standings are final.</Info>;

  const options = data.date_options;
  // The date to show on the slider: the one you picked, or the API's default if you haven't
  // picked one. Using your pick (not data.date) keeps the slider where you left it while
  // the new numbers are still loading; the tables catch up a moment later.
  const shownDate = date ?? data.date;
  // Where the slider sits: the position of that date in the list of options.
  const position = Math.max(0, options.indexOf(shownDate));

  const columns: Column<ProjectedRow>[] = [
    { header: "Rank", cell: (_row, index) => index + 1, numeric: true },
    { header: "Team", cell: (row) => <Team code={row.team} /> },
    { header: "W", cell: (row) => row.W.toFixed(1), numeric: true },
    { header: "L", cell: (row) => row.L.toFixed(1), numeric: true },
  ];

  return (
    <section>
      <label className="mb-4 block max-w-xl text-sm">
        Predicted standings on <strong>{longDate(shownDate)}</strong>
        {loading && <span className="ml-2 text-zinc-500">(updating...)</span>}
        {/* A range slider over the list positions 0, 1, 2, ...; moving it picks options[position]. */}
        <input
          type="range"
          min={0}
          max={options.length - 1}
          value={position}
          onChange={(event) => setDate(options[Number(event.target.value)])}
          className="mt-2 w-full accent-orange-500"
        />
        <span className="flex justify-between text-xs text-zinc-500">
          <span>{longDate(options[0])}</span>
          <span>{longDate(options[options.length - 1])}</span>
        </span>
      </label>

      <div className="grid gap-6 md:grid-cols-2">
        {(["East", "West"] as const).map((conference) => (
          <div key={conference}>
            <h2 className="mb-2 text-xl font-semibold">{conference}</h2>
            <Table columns={columns} rows={data[conference]} rowKey={(row) => row.team} maxHeight="none" />
          </div>
        ))}
      </div>
      <Caption>Expected record: current wins plus the win chances of every game until that date.</Caption>
    </section>
  );
}
