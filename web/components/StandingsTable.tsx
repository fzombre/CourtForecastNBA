"use client";

// Tab 3 (Standings): live East and West standings side by side, with games behind.
// A solid line under seed 6 marks the playoff cut, a dashed line under seed 10 the
// play-in cut (see seedRule and SeedLegend in Table.tsx).

import { useApi } from "./SettingsProvider";
import Table, { Heading, LoadingOrError, SeedLegend, seedRule, type Column } from "./Table";
import Team from "./Team";
import { gamesBehind, winPct } from "@/lib/format";
import type { Conference, Standings, StandingsRow } from "@/lib/types";

const COLUMNS: Column<StandingsRow>[] = [
  // Rows arrive already sorted, so the position in the list is the seed.
  { header: "Seed", cell: (_row, index) => index + 1, numeric: true, className: "w-12 text-muted" },
  { header: "Team", cell: (row) => <Team code={row.team} compact /> },
  { header: "W", cell: (row) => row.W, numeric: true },
  { header: "L", cell: (row) => row.L, numeric: true },
  { header: "PCT", cell: (row) => winPct(row.PCT), numeric: true },
  { header: "GB", cell: (row) => gamesBehind(row.GB), numeric: true },
];

// `as const` tells TypeScript this list holds exactly "East" and "West", not any string,
// so data[conference] is known to be a list of StandingsRow.
const CONFERENCES = ["East", "West"] as const satisfies readonly Conference[];

export default function StandingsTable() {
  const { data, error } = useApi<Standings>("/api/standings");

  if (!data) return <LoadingOrError error={error} what="standings" />;

  return (
    <section>
      <SeedLegend />
      <div className="grid gap-x-12 gap-y-10 lg:grid-cols-2">
        {CONFERENCES.map((conference) => (
          <div key={conference}>
            <Heading className="mb-3">{conference}</Heading>
            <Table
              columns={COLUMNS}
              rows={data[conference]}
              rowKey={(row) => row.team}
              rowRule={seedRule}
              maxHeight="none"
              label={`${conference} standings`}
            />
          </div>
        ))}
      </div>
    </section>
  );
}
