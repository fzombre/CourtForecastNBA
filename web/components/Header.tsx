"use client";

// Header: the sticky bar across the top of every page. It holds:
//   - the wordmark (a link home),
//   - the tabs (NavTabs),
//   - a "data status" button: what the Streamlit sidebar showed (season, where the data
//     came from, which model is active), tucked into a small popover so it's one click
//     away without taking up a line on every page,
//   - the refresh button, which confirms with a short message (a "toast") when it's done.
//
// The bar is slightly see-through with a blur behind it (backdrop-blur), so while you
// scroll you can still sense the content passing underneath.
//
// (The sidebar's "Simulated seasons" picker is gone on purpose: the app decides how many
// seasons to simulate, see N_SIMS in src/api.py.)

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { useDismiss } from "@/lib/useDismiss";
import type { Overview } from "@/lib/types";
import { RefreshIcon } from "./Icons";
import NavTabs from "./NavTabs";
import { useSettings } from "./SettingsProvider";

// ---------------------------------------------------------------------------------------
// Data status popover
// ---------------------------------------------------------------------------------------

/** "live (nba_api)" -> true. The API reports the source as "live (...)" or "saved copy (...)". */
const isLive = (info: Overview) => info.source.startsWith("live");

function DataStatus() {
  const { overview } = useSettings();
  const info = overview.data;
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  useDismiss(rootRef, open, () => setOpen(false));

  // What the button says: the API's state at a glance.
  const offline = Boolean(overview.error);
  const label = offline ? "API offline" : !info ? "Connecting…" : isLive(info) ? "Live data" : "Saved data";

  return (
    <div ref={rootRef} className="relative">
      <button
        type="button"
        aria-expanded={open}
        aria-haspopup="dialog"
        onClick={() => setOpen((o) => !o)}
        className="inline-flex h-9 items-center gap-2 rounded-full border border-line px-3 text-sm text-fg transition-colors hover:bg-raised"
      >
        {/* The dot: red when the API can't be reached, gold when the data is live,
            muted for a saved copy. The text next to it always says the same thing,
            so the color is never the only signal. */}
        <span
          aria-hidden
          className={`size-2 rounded-full ${offline ? "bg-live" : info && isLive(info) ? "bg-pick" : "bg-muted"}`}
        />
        <span className="hidden sm:inline">{label}</span>
        {info && <span className="text-muted tabular-nums">{info.season.replace("-", "–")}</span>}
      </button>

      {open && (
        <div
          role="dialog"
          aria-label="Data status"
          className="absolute top-full right-0 z-40 mt-2 w-[min(20rem,calc(100vw-2rem))] rounded-xl border border-line-strong bg-raised p-4 text-sm shadow-[0_16px_40px_-12px_rgb(0_0_0/0.7)]"
        >
          {offline ? (
            <p>
              The Python API isn&apos;t answering. Start it with{" "}
              <code className="rounded bg-canvas px-1 py-0.5 text-[13px]">
                py -m uvicorn api:app --app-dir src --port 8000
              </code>
              , then press refresh.
              <span className="mt-2 block break-words text-muted">{overview.error}</span>
            </p>
          ) : info ? (
            // A definition list: each term (dt) on the left, its value (dd) on the right.
            <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-2.5">
              <dt className="text-muted">Season</dt>
              <dd>{info.season.replace("-", "–")}</dd>
              <dt className="text-muted">Data</dt>
              <dd>{isLive(info) ? "Live from NBA.com" : `The ${info.source}`}</dd>
              <dt className="text-muted">Picks</dt>
              <dd>
                {info.using_model
                  ? `Trained model, learned from ${info.training_games} finished games`
                  : `Plain Elo ratings until more games are finished (${info.training_games} so far)`}
              </dd>
              <dt className="text-muted">Odds</dt>
              <dd>{info.n_sims.toLocaleString()} simulated seasons</dd>
            </dl>
          ) : (
            <p className="text-muted">Connecting to the Python API…</p>
          )}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------------------
// Refresh button + toast
// ---------------------------------------------------------------------------------------

type Toast = { text: string; failed: boolean; id: number };

function RefreshButton() {
  const { refresh, refreshing } = useSettings();
  const [toast, setToast] = useState<Toast | null>(null);

  // Each toast disappears by itself after a few seconds. A new toast (new id) restarts the clock.
  useEffect(() => {
    if (!toast) return;
    const timer = setTimeout(() => setToast(null), toast.failed ? 6000 : 3000);
    return () => clearTimeout(timer);
  }, [toast]);

  const onClick = async () => {
    try {
      await refresh();
      // The button is called "Refresh data", so the confirmation says "Data refreshed".
      setToast({ text: "Data refreshed", failed: false, id: Date.now() });
    } catch (err) {
      setToast({
        text: `Couldn't refresh: ${err instanceof Error ? err.message : String(err)}`,
        failed: true,
        id: Date.now(),
      });
    }
  };

  return (
    <>
      <button
        type="button"
        onClick={onClick}
        disabled={refreshing}
        aria-label={refreshing ? "Refreshing data" : "Refresh data"}
        title="Refresh data"
        className="inline-flex size-9 items-center justify-center rounded-full border border-line text-fg transition-colors hover:bg-raised disabled:cursor-wait"
      >
        {/* The arrows spin while the refresh runs (and stay still for reduced motion). */}
        <RefreshIcon className={refreshing ? "animate-spin text-pick motion-reduce:animate-none" : ""} />
      </button>

      {/* role="status": screen readers announce the toast's text when it appears. The
          wrapper is always on the page (only its contents change), which is what makes
          the announcement reliable. */}
      <div
        role="status"
        className="pointer-events-none fixed inset-x-4 bottom-4 z-50 flex justify-center sm:inset-x-auto sm:right-6 sm:bottom-6"
      >
        {toast && (
          <p
            key={toast.id}
            className={`toast-in pointer-events-auto flex max-w-sm items-center gap-2.5 rounded-xl border bg-raised px-4 py-3 text-sm shadow-[0_16px_40px_-12px_rgb(0_0_0/0.8)] ${
              toast.failed ? "border-live/50" : "border-line-strong"
            }`}
          >
            <span aria-hidden className={`size-2 shrink-0 rounded-full ${toast.failed ? "bg-live" : "bg-pick"}`} />
            {toast.text}
          </p>
        )}
      </div>
    </>
  );
}

// ---------------------------------------------------------------------------------------
// The bar itself
// ---------------------------------------------------------------------------------------

export default function Header() {
  return (
    <header className="sticky top-0 z-30 border-b border-line bg-canvas/80 backdrop-blur-md">
      {/* .topbar (globals.css) arranges brand / tabs / actions in one or two rows. */}
      <div className="topbar mx-auto max-w-6xl px-4 md:px-8">
        <Link
          href="/"
          style={{ gridArea: "brand" }}
          className="font-display text-[1.7rem] leading-none font-extrabold tracking-tight"
        >
          CourtForecastNBA
        </Link>

        <div style={{ gridArea: "tabs" }} className="min-w-0 self-stretch">
          <NavTabs />
        </div>

        <div style={{ gridArea: "actions" }} className="flex items-center gap-2">
          <DataStatus />
          <RefreshButton />
        </div>
      </div>
    </header>
  );
}
