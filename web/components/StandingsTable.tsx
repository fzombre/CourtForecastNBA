"use client"; // runs in the browser, because it uses useState/useEffect

import { useEffect, useState } from "react";
import { getStandings } from "@/lib/api";
import type { Standings } from "@/lib/types";

/** Tab 3 of the Streamlit app: East and West standings side by side. */
export default function StandingsTable() {
  const [data, setData] = useState<Standings | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getStandings().then(setData).catch((e: Error) => setError(e.message));
  }, []); // [] = run once, when the component first appears

  if (error) return <p className="text-red-600">Could not load standings: {error}</p>;
  if (!data) return <p>Loading standings...</p>;

  return (
    <div className="grid gap-8 md:grid-cols-2">
      {(["East", "West"] as const).map((conference) => (
        <table key={conference} className="text-sm">
          <caption className="text-left text-lg font-semibold">{conference}</caption>
          <thead>
            <tr><th>Rank</th><th>Team</th><th>W</th><th>L</th><th>PCT</th><th>GB</th></tr>
          </thead>
          <tbody>
            {data[conference].map((row, index) => (
              <tr key={row.team}>
                <td>{index + 1}</td><td>{row.team}</td><td>{row.W}</td><td>{row.L}</td>
                <td>{row.PCT.toFixed(3)}</td><td>{row.GB}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ))}
    </div>
  );
}
