"use client";

// Tab 5 (Playoff odds): each team's chances to make the playoffs, reach each round and
// win the title, from the Monte Carlo simulation in simulate.py.
//
// The round-by-round columns are shaded like a heat map: the higher the chance, the more
// of the accent color fills the cell. Reading across a row, the color fades as the rounds
// get harder, so you can see how deep each team is expected to go without reading numbers.

import { useState, type CSSProperties } from "react";
import { useApi, useSettings } from "./SettingsProvider";
import Table, { Caption, LoadingOrError, type Column } from "./Table";
import { Segmented } from "./Controls";
import Team, { TeamLogo } from "./Team";
import { percent } from "@/lib/format";
import type { TeamOdds } from "@/lib/types";

/**
 * The cell shade for a chance of `value` percent, on a single-hue blue ramp: one hue
 * getting stronger is the right encoding for "more of the same thing".
 *
 *  - Under 0.5% (shown as "0.0%" or "0.4%") the cell has no shade at all, so the many
 *    near-zero title chances don't fill the table with boxes.
 *  - Above that, the cell starts at the pale --heat blue and mixes in more of the accent
 *    as the chance grows, up to 50% accent at a 100% chance. The cap keeps the ink text
 *    readable on the darkest cells (about 5:1 in both light and dark mode).
 */
function heat(value: number): CSSProperties | undefined {
  if (value < 0.5) return undefined;
  const strength = Math.round((Math.min(100, value) / 100) * 50);
  return { backgroundColor: `color-mix(in oklab, var(--paint) ${strength}%, var(--heat))` };
}

/** One shaded odds column. `field` is which number of TeamOdds to show. */
function oddsColumn(header: string, field: keyof Pick<TeamOdds, "playoffs" | "round_2" | "conf_finals" | "finals" | "champion">): Column<TeamOdds> {
  return {
    header,
    cell: (t) => percent(t[field]),
    numeric: true,
    cellStyle: (t) => heat(t[field]),
    className: "min-w-24",
  };
}

const COLUMNS: Column<TeamOdds>[] = [
  { header: "Team", cell: (t) => <Team code={t.team} compact /> },
  { header: "Conf", cell: (t) => t.conference, className: "text-ink-muted" },
  { header: "Proj W", cell: (t) => t.proj_W.toFixed(1), numeric: true },
  { header: "Proj L", cell: (t) => t.proj_L.toFixed(1), numeric: true },
  { header: "Avg seed", cell: (t) => t.avg_seed.toFixed(1), numeric: true },
  oddsColumn("Playoffs", "playoffs"),
  oddsColumn("2nd round", "round_2"),
  oddsColumn("Conf finals", "conf_finals"),
  oddsColumn("Finals", "finals"),
  oddsColumn("Title", "champion"),
];

const CONFERENCE_FILTERS = ["All", "East", "West"] as const;
type ConferenceFilter = (typeof CONFERENCE_FILTERS)[number];

export default function OddsTab() {
  const { overview, teamName } = useSettings();
  const { data: odds, error, loading } = useApi<TeamOdds[]>("/api/odds");
  const [conference, setConference] = useState<ConferenceFilter>("All");
  // How many seasons the API simulated (its own setting). Undefined until the overview has loaded.
  const nSims = overview.data?.n_sims;

  // The first simulation after a download takes a few seconds, so say so while waiting.
  if (!odds) return <LoadingOrError error={error} what="playoff odds (the simulation takes a few seconds)" />;

  const favorite = odds[0]; // the API sends the teams sorted by title odds, best first
  const shown = conference === "All" ? odds : odds.filter((t) => t.conference === conference);

  return (
    <section>
      {favorite && (
        // The favorite gets a short sentence, not a stat tile: the logo, the name in the
        // display face, and the chance written out.
        <div className="mb-8 flex items-center gap-4">
          <TeamLogo code={favorite.team} size={56} />
          <div>
            <p className="text-sm text-ink-muted">Title favorite</p>
            <p className="font-display text-4xl leading-none font-extrabold tracking-tight">{teamName(favorite.team)}</p>
            <p className="mt-1 text-[15px]">
              <strong className="font-semibold">{percent(favorite.champion)}</strong> chance to win the championship
            </p>
          </div>
        </div>
      )}

      <div className="mb-4 flex flex-wrap items-center gap-x-6 gap-y-3">
        <Segmented label="Conference" value={conference} options={CONFERENCE_FILTERS} onChange={setConference} />
        <Caption className="my-0">
          From {nSims ? nSims.toLocaleString() : "thousands of"} simulated seasons, including the play-in and every
          playoff round.
          {loading && " Updating…"}
        </Caption>
      </div>
      <Table columns={COLUMNS} rows={shown} rowKey={(t) => t.team} maxHeight="none" label="Playoff and title odds" />
    </section>
  );
}
