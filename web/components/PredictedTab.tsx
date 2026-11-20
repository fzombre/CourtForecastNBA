"use client";

// Tab 4 (Predicted standings): expected records on a future date, picked with a slider.
// The math (current wins + the win chances of every game until that date) runs in
// Python: forecast.expected_wins_by_date(). This component only draws the result.
//
// The date control sits in its own panel: the picked date in large display type (the one
// thing you're changing, so it stays in view and updates as you drag), a custom slider
// filled in gold up to the thumb, and back/forward buttons to step one date at a time.

import { useState, type CSSProperties, type ReactNode } from "react";
import { useApi } from "./SettingsProvider";
import Table, { Caption, Heading, Info, LoadingOrError, SeedLegend, seedRule, type Column } from "./Table";
import { ChevronLeftIcon, ChevronRightIcon } from "./Icons";
import Team from "./Team";
import { longDate, winPct } from "@/lib/format";
import type { ProjectedRow, ProjectedStandings } from "@/lib/types";

const COLUMNS: Column<ProjectedRow>[] = [
  { header: "Seed", cell: (_row, index) => index + 1, numeric: true, className: "w-12 text-muted" },
  { header: "Team", cell: (row) => <Team code={row.team} compact /> },
  // Expected wins are averages, so they have one decimal (e.g. 41.3).
  { header: "W", cell: (row) => row.W.toFixed(1), numeric: true },
  { header: "L", cell: (row) => row.L.toFixed(1), numeric: true },
  { header: "PCT", cell: (row) => winPct(row.PCT), numeric: true },
];

/** A round button with an arrow, for stepping the date one option back or forward. */
function StepButton({ label, disabled, onClick, children }: { label: string; disabled: boolean; onClick: () => void; children: ReactNode }) {
  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      disabled={disabled}
      onClick={onClick}
      className="inline-flex size-9 shrink-0 items-center justify-center rounded-full border border-line-strong text-fg transition-colors hover:bg-raised disabled:cursor-not-allowed disabled:opacity-35 disabled:hover:bg-transparent"
    >
      {children}
    </button>
  );
}

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
  const last = options.length - 1;
  // How far along the slider is, as a percentage, for the gold fill (--fill in globals.css).
  const fill = last > 0 ? (position / last) * 100 : 0;

  /** Move to the option at `index`, kept inside the list. */
  const go = (index: number) => setDate(options[Math.max(0, Math.min(last, index))]);

  return (
    <section>
      <div className="mb-10 max-w-2xl rounded-2xl border border-line bg-panel p-5 md:p-6">
        <div className="flex items-end justify-between gap-4">
          <div>
            <p id="date-label" className="text-sm text-muted">
              Standings as of
            </p>
            <p className="mt-1.5 font-display text-4xl leading-none font-extrabold tracking-tight sm:text-5xl">
              {longDate(shownDate)}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <StepButton label="Previous date" disabled={position === 0} onClick={() => go(position - 1)}>
              <ChevronLeftIcon />
            </StepButton>
            <StepButton label="Next date" disabled={position === last} onClick={() => go(position + 1)}>
              <ChevronRightIcon />
            </StepButton>
          </div>
        </div>

        {/* A range slider over the list positions 0, 1, 2, ...; moving it picks options[position].
            It's still a real <input type="range">, so arrow keys, Home/End and touch all
            work; .date-range only changes how it looks. aria-valuetext makes screen
            readers say the date instead of "position 3". */}
        <input
          type="range"
          min={0}
          max={last}
          value={position}
          aria-labelledby="date-label"
          aria-valuetext={longDate(shownDate)}
          onChange={(event) => go(Number(event.target.value))}
          className="date-range mt-7 w-full"
          style={{ "--fill": `${fill}%` } as CSSProperties}
        />
        <div className="mt-3 flex justify-between text-xs text-muted tabular-nums">
          <span>{longDate(options[0])}</span>
          {/* While the new numbers load, the tables below are briefly the old date's. Say so. */}
          <span aria-live="polite" className="text-pick">
            {loading ? "Updating…" : ""}
          </span>
          <span>{longDate(options[last])}</span>
        </div>
      </div>

      <SeedLegend />

      {/* Dim the tables slightly while they show the previous date's numbers. */}
      <div className={`grid gap-x-10 gap-y-12 transition-opacity lg:grid-cols-2 ${loading ? "opacity-60" : ""}`}>
        {(["East", "West"] as const).map((conference) => (
          <div key={conference}>
            <Heading className="mb-4">{conference}</Heading>
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
