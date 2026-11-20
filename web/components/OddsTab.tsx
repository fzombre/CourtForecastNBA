"use client";

// Tab 5 (Playoff odds): each team's chances to make the playoffs, reach each round and
// win the title, from the Monte Carlo simulation in simulate.py.
//
// At the top: the title favorite, with the next two contenders beside it.
// Below: the full table. The round-by-round columns are shaded like a heat map: the
// higher the chance, the more periwinkle fills the cell. Reading across a row, the color
// fades as the rounds get harder, so you can see how deep each team is expected to go
// without reading every number.

import { useState, type CSSProperties } from "react";
import { useApi, useSettings } from "./SettingsProvider";
import Table, { Caption, LoadingOrError, type Column } from "./Table";
import { Segmented } from "./Controls";
import Team, { TeamLogo } from "./Team";
import { percent } from "@/lib/format";
import type { TeamOdds } from "@/lib/types";

/**
 * The cell shade for a chance of `value` percent, on a single-hue ramp: one hue getting
 * stronger is the right encoding for "more of the same thing".
 *
 *  - Under 0.5% (shown as "0.0%" to "0.4%") the cell isn't shaded at all, so the many
 *    near-zero title chances don't fill the table with boxes.
 *  - Above that, periwinkle is mixed into the panel color, from a faint tint up to 55%
 *    periwinkle at a 100% chance. Mixing into the panel (not making it see-through)
 *    keeps the shades exact. The cap keeps the maple text readable on the strongest
 *    cells (about 5:1).
 */
function heat(value: number): CSSProperties | undefined {
  if (value < 0.5) return undefined;
  const strength = Math.round(6 + (Math.min(100, value) / 100) * 49); // 6% .. 55%
  return { backgroundColor: `color-mix(in oklab, var(--metric) ${strength}%, var(--panel))` };
}

type OddsField = keyof Pick<TeamOdds, "playoffs" | "round_2" | "conf_finals" | "finals" | "champion">;

/** One shaded odds column. `field` is which number of TeamOdds to show. */
function oddsColumn(header: string, field: OddsField): Column<TeamOdds> {
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
  { header: "Conf", cell: (t) => t.conference, className: "text-muted" },
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

/** The favorite: big logo, the name in display type, and the title chance written out. */
function Favorite({ team }: { team: TeamOdds }) {
  const { teamName } = useSettings();
  return (
    <div className="flex items-center gap-5">
      <TeamLogo code={team.team} size={72} />
      <div className="min-w-0">
        <p className="text-sm text-muted">Title favorite</p>
        <p className="font-display text-4xl leading-none font-extrabold tracking-tight sm:text-5xl">
          {teamName(team.team)}
        </p>
        <p className="mt-2 text-[15px]">
          <strong className="font-semibold text-pick">{percent(team.champion)}</strong> chance to win the championship
        </p>
      </div>
    </div>
  );
}

export default function OddsTab() {
  const { overview } = useSettings();
  const { data: odds, error, loading } = useApi<TeamOdds[]>("/api/odds");
  const [conference, setConference] = useState<ConferenceFilter>("All");
  // How many seasons the API simulated (its own setting). Undefined until the overview has loaded.
  const nSims = overview.data?.n_sims;

  // The first simulation after a download takes a few seconds, so say so while waiting.
  if (!odds) return <LoadingOrError error={error} what="playoff odds (the simulation takes a few seconds)" rows={12} />;

  // The API sends the teams sorted by title odds, best first.
  const [favorite, ...rest] = odds;
  const contenders = rest.slice(0, 2);
  const shown = conference === "All" ? odds : odds.filter((t) => t.conference === conference);

  return (
    <section>
      {favorite && (
        // The one framed strip on this page: the answer to "who's going to win it all?"
        <div className="mb-10 flex flex-wrap items-center justify-between gap-x-10 gap-y-6 rounded-2xl border border-line bg-panel p-5 md:p-6">
          <Favorite team={favorite} />
          {contenders.length > 0 && (
            <div>
              <p className="mb-2 text-sm text-muted">Next in line</p>
              <ol className="space-y-2">
                {contenders.map((t) => (
                  <li key={t.team} className="flex items-center justify-between gap-6 text-[15px]">
                    <Team code={t.team} />
                    <span className="tabular-nums">{percent(t.champion)}</span>
                  </li>
                ))}
              </ol>
            </div>
          )}
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
