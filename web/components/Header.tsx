"use client";

// Header: the title plus everything the Streamlit sidebar had: the season, where the
// data came from, which model is active, the "Simulated seasons" picker and the refresh button.

import { useSettings } from "./SettingsProvider";

/** Used until the overview has loaded and tells us the real choices. */
const FALLBACK_SIM_CHOICES = [500, 1000, 2000, 5000, 10000];

export default function Header() {
  const { sims, setSims, refresh, refreshing, overview } = useSettings();
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

      <div className="flex items-end gap-3">
        <label className="flex flex-col text-sm">
          Simulated seasons
          {/* Number(...) because a <select> always hands back its value as text. */}
          <select
            value={sims}
            onChange={(event) => setSims(Number(event.target.value))}
            className="rounded border border-zinc-300 bg-transparent px-2 py-1 dark:border-zinc-700"
            title="More simulations = steadier odds, but slower."
          >
            {(info?.sim_choices ?? FALLBACK_SIM_CHOICES).map((choice) => (
              <option key={choice} value={choice}>
                {choice.toLocaleString()}
              </option>
            ))}
          </select>
        </label>
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
