"use client";

// Tab 3 (Standings): live East and West standings side by side, with games behind.

import { useApi } from "./SettingsProvider";
import Table, { Caption, LoadingOrError, type Column } from "./Table";
import Team from "./Team";
import type { Conference, Standings, StandingsRow } from "@/lib/types";

export default function StandingsTable() {
  const { data, error } = useApi<Standings>("/api/standings");

  if (!data) return <LoadingOrError error={error} what="standings" />;

  const columns: Column<StandingsRow>[] = [
    { header: "Rank", cell: (_row, index) => index + 1, numeric: true }, // rows arrive already sorted
    { header: "Team", cell: (row) => <Team code={row.team} /> },
    { header: "W", cell: (row) => row.W, numeric: true },
    { header: "L", cell: (row) => row.L, numeric: true },
    { header: "PCT", cell: (row) => row.PCT.toFixed(3), numeric: true },
    { header: "GB", cell: (row) => row.GB, numeric: true },
  ];

  // `as const` tells TypeScript this list holds exactly "East" and "West", not any string,
  // so data[conference] is known to be a list of StandingsRow.
  const conferences = ["East", "West"] as const satisfies readonly Conference[];

  return (
    <section>
      <div className="grid gap-6 md:grid-cols-2">
        {conferences.map((conference) => (
          <div key={conference}>
            <h2 className="mb-2 text-xl font-semibold">{conference}</h2>
            <Table columns={columns} rows={data[conference]} rowKey={(row) => row.team} maxHeight="none" />
          </div>
        ))}
      </div>
      <Caption>Seeds 1-6 make the playoffs, 7-10 go to the play-in tournament.</Caption>
    </section>
  );
}
