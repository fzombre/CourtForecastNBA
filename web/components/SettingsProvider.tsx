"use client";

// SettingsProvider: the things every tab shares, like the Streamlit sidebar.
//
//   - refresh:  forget the cached data and load everything again (the 🔄 button)
//   - overview: season, data source, model info and team names, loaded once for all tabs
//
// (How many seasons to simulate is not a setting here: the Python API picks that
// itself, N_SIMS in src/api.py, because it's about prediction quality, not a user choice.)
//
// It uses React "context": the provider wraps the whole site in app/layout.tsx, and any
// component inside it can read these values with useSettings() instead of receiving
// them through props layer by layer. Because the layout stays on screen when you switch
// tabs, the overview is loaded once instead of again on every page.

import { createContext, useCallback, useContext, useState, type ReactNode } from "react";
import { postJson } from "@/lib/api";
import { useFetch, type FetchState } from "@/lib/useFetch";
import type { Overview } from "@/lib/types";

type Settings = {
  /** Goes up by one on every refresh, which makes every useApi() request run again. */
  version: number;
  refresh: () => Promise<void>;
  refreshing: boolean;
  overview: FetchState<Overview>;
  /** "BOS" -> "Boston Celtics". Falls back to the code until the names have loaded. */
  teamName: (code: string | null | undefined) => string;
  /** "BOS" -> 1610612738 (for the logo). undefined until the overview has loaded. */
  teamId: (code: string) => number | undefined;
};

// null until a provider is on the page; useSettings() checks for that below.
const SettingsContext = createContext<Settings | null>(null);

export default function SettingsProvider({ children }: { children: ReactNode }) {
  const [version, setVersion] = useState(0);
  const [refreshing, setRefreshing] = useState(false);

  const overview = useFetch<Overview>("/api/overview", version);

  const refresh = useCallback(async () => {
    setRefreshing(true);
    try {
      await postJson("/api/refresh"); // the Python API empties its caches...
      setVersion((v) => v + 1); // ...and every component asks for its data again
    } finally {
      setRefreshing(false); // runs even if the request failed, so the button never stays stuck
    }
  }, []);

  const names = overview.data?.team_names;
  const teamName = useCallback((code: string | null | undefined) => (code ? (names?.[code] ?? code) : ""), [names]);
  const ids = overview.data?.team_ids;
  const teamId = useCallback((code: string) => ids?.[code], [ids]);

  return (
    <SettingsContext.Provider value={{ version, refresh, refreshing, overview, teamName, teamId }}>
      {children}
    </SettingsContext.Provider>
  );
}

/** Read the shared settings from any component inside <SettingsProvider>. */
export function useSettings(): Settings {
  const settings = useContext(SettingsContext);
  if (settings === null) throw new Error("useSettings() must be used inside <SettingsProvider>");
  return settings;
}

/** useFetch() that also reloads when the refresh button is pressed. What the tabs use. */
export function useApi<T>(path: string | null): FetchState<T> {
  return useFetch<T>(path, useSettings().version);
}
