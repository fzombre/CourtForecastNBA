"use client";

// Header: the title plus what the Streamlit sidebar showed: the season, where the data
// came from, which model is active, and the refresh button.
// (The sidebar's "Simulated seasons" picker is gone on purpose: the app decides how many
// seasons to simulate, see N_SIMS in src/api.py.)

import { useSettings } from "./SettingsProvider";

export default function Header() {
  const { refresh, refreshing, overview } = useSettings();
  const info = overview.data;

  return (
    <header className="mb-4 flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 className="text-3xl font-bold">🏀 CourtForecastNBA{info ? ` · ${info.season}` : ""}</h1>
        {info && (
          <p className="text-sm text-zinc-500">
            Season {info.season} · data: {info.source} · model trained on {info.training_games} finished games
            {info.using_model ? "" : " (too few yet, using plain Elo)"}
          </p>
        )}
        {overview.error && <p className="text-sm text-red-600">Could not reach the Python API: {overview.error}</p>}
      </div>

      <div>
        <button
          onClick={refresh}
          disabled={refreshing}
          className="rounded border border-zinc-300 px-3 py-1 text-sm hover:bg-zinc-100 disabled:opacity-50 dark:border-zinc-700 dark:hover:bg-zinc-900"
        >
          {refreshing ? "Refreshing..." : "🔄 Refresh data"}
        </button>
      </div>
    </header>
  );
}
