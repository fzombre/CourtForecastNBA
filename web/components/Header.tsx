"use client";

// Header: the wordmark plus what the Streamlit sidebar showed: the season, where the data
// came from, which model is active, and the refresh button.
// (The sidebar's "Simulated seasons" picker is gone on purpose: the app decides how many
// seasons to simulate, see N_SIMS in src/api.py.)

import { useSettings } from "./SettingsProvider";
import type { Overview } from "@/lib/types";

/**
 * One plain sentence about the data and the model, e.g.
 *   "Live data from NBA.com. Model trained on 412 finished games."
 * Written as a sentence instead of "A · B · C" so it reads like an explanation, not a log line.
 */
function statusSentence(info: Overview): string {
  // The API reports the source as "live (nba_api)" or "saved copy (...)".
  const data = info.source.startsWith("live")
    ? "Live data from NBA.com."
    : `Offline: using the ${info.source} of the data.`;
  const model = info.using_model
    ? `Model trained on ${info.training_games} finished games.`
    : `Picks use plain Elo ratings until more games are finished (${info.training_games} so far).`;
  return `${data} ${model}`;
}

export default function Header() {
  const { refresh, refreshing, overview } = useSettings();
  const info = overview.data;

  return (
    <header className="flex flex-wrap items-end justify-between gap-x-8 gap-y-4">
      <div className="min-w-0">
        {/* The wordmark. Big Shoulders is very condensed, so it can be set large without
            wrapping, and the season sits beside it at a lighter weight like a jersey number. */}
        <h1 className="font-display text-5xl leading-none font-extrabold tracking-tight sm:text-6xl">
          CourtForecastNBA
          {/* The {" "} space is a place the line may break on narrow screens; without it
              the browser treats "CourtForecastNBA2026–" as one word and it runs off a phone.
              whitespace-nowrap keeps the season itself from splitting at its dash. */}
          {info && " "}
          {info && (
            <span className="font-semibold whitespace-nowrap text-ink-muted">
              {/* "2026-27" -> "2026–27": a year range takes an en dash. */}
              {info.season.replace("-", "–")}
            </span>
          )}
        </h1>
        {info && <p className="mt-3 max-w-prose text-sm text-ink-muted">{statusSentence(info)}</p>}
        {overview.error && (
          <p className="mt-3 max-w-prose text-sm text-live">
            Can&apos;t reach the Python API. Start it with{" "}
            <code className="font-semibold">py -m uvicorn api:app --app-dir src --port 8000</code>, then press Refresh
            data. ({overview.error})
          </p>
        )}
      </div>

      <button
        onClick={refresh}
        disabled={refreshing}
        className="rounded-full border border-ink px-4 py-1.5 text-sm font-medium transition-colors hover:bg-ink hover:text-floor disabled:cursor-wait disabled:opacity-60"
      >
        {refreshing ? "Refreshing…" : "Refresh data"}
      </button>
    </header>
  );
}
