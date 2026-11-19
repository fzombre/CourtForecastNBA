"use client";

// Tab 4 (Predicted standings): expected records on a future date, picked with a slider.
// The math (current wins + the win chances of every game until that date) runs in
// Python: forecast.expected_wins_by_date(). This component only draws the result.
//
// The picked date is the biggest type on the page: it's the one thing you're changing,
// so it stays in view and updates as you drag.

import { useState } from "react";
import { useApi } from "./SettingsProvider";
import Table, { Caption, Heading, Info, LoadingOrError, SeedLegend, seedRule, type Column } from "./Table";
import Team from "./Team";
import { longDate, winPct } from "@/lib/format";
import type { ProjectedRow, ProjectedStandings } from "@/lib/types";

const COLUMNS: Column<ProjectedRow>[] = [
  { header: "Seed", cell: (_row, index) => index + 1, numeric: true, className: "w-12 text-ink-muted" },
  { header: "Team", cell: (row) => <Team code={row.team} compact /> },
  // Expected wins are averages, so they have one decimal (e.g. 41.3).
  { header: "W", cell: (row) => row.W.toFixed(1), numeric: true },
  { header: "L", cell: (row) => row.L.toFixed(1), numeric: true },
  { header: "PCT", cell: (row) => winPct(row.PCT), numeric: true },
];

export default function PredictedTab() {
  // The date picked on the slider. null = "none picked yet", which makes the API choose
  // the first option (a week from today) and send us the list of all options.
  const [date, setDate] = useState<string | null>(null);

  const path = "/api/projected-standings" + (date ? `?date=${date}` : "");
  const { data, error, loading } = useApi<ProjectedStandings>(path);

  if (!data) return <LoadingOrError error={error} what="predicted standings" />;
  if (data.date === null) return <Info>The regular season is over, so the standings are final.</Info>;

  // The date the tables are for right now. Saved in a const because TypeScript forgets the
  // "not null" check above inside the .map() callback below, but remembers it for a const.
  const tablesDate = data.date;
  const options = data.date_options;
  // The date to show on the slider: the one you picked, or the API's default if you haven't
  // picked one. Using your pick (not data.date) keeps the slider where you left it while
  // the new numbers are still loading; the tables catch up a moment later.
  const shownDate = date ?? data.date;
  // Where the slider sits: the position of that date in the list of options.
  const position = Math.max(0, options.indexOf(shownDate));

  return (
    <section>
      {/* The <label> wraps the slider, so clicking the date text focuses the slider and
          screen readers read the date as the slider's name. */}
      <label className="block max-w-2xl">
        <span className="block text-sm text-ink-muted">Standings as of</span>
        <span className="mt-1 flex items-baseline gap-3">
          <span className="font-display text-5xl leading-none font-extrabold tracking-tight tabular-nums">
            {longDate(shownDate)}
          </span>
          {/* While the new numbers load, the tables below are briefly the old date's. Say so. */}
          {loading && (
            <span aria-live="polite" className="text-sm text-ink-muted">
              Updating…
            </span>
          )}
        </span>
        {/* A range slider over the list positions 0, 1, 2, ...; moving it picks options[position].
            accent-paint colors the native slider in the accent, keeping the browser's
            built-in keyboard and touch handling. */}
        <input
          type="range"
          min={0}
          max={options.length - 1}
          value={position}
          aria-valuetext={longDate(shownDate)}
          onChange={(event) => setDate(options[Number(event.target.value)])}
          className="mt-5 w-full cursor-pointer accent-paint"
        />
        <span className="mt-1 flex justify-between text-xs text-ink-muted">
          <span>{longDate(options[0])}</span>
          <span>{longDate(options[options.length - 1])}</span>
        </span>
      </label>

      <SeedLegend />

      {/* Dim the tables slightly while they show the previous date's numbers. */}
      <div className={`grid gap-x-12 gap-y-10 transition-opacity lg:grid-cols-2 ${loading ? "opacity-60" : ""}`}>
        {(["East", "West"] as const).map((conference) => (
          <div key={conference}>
            <Heading className="mb-3">{conference}</Heading>
            <Table
              columns={COLUMNS}
              rows={data[conference]}
              rowKey={(row) => row.team}
              rowRule={seedRule}
              maxHeight="none"
              label={`Predicted ${conference} standings on ${longDate(tablesDate)}`}
            />
          </div>
        ))}
      </div>
      <Caption className="mt-6">
        Expected record: current wins plus the win chances of every game until that date.
      </Caption>
    </section>
  );
}
