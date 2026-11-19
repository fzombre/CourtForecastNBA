"use client";

// useFetch: a React hook that loads JSON from the API and keeps track of
// "still loading", "failed" and "here's the data" for you.
//
// Every tab needs the same three things, so they live here once instead of in every component.

import { useEffect, useState } from "react";
import { getJson } from "./api";

export type FetchState<T> = {
  /** The latest data that arrived. While a new request is running this is still the
   *  previous answer, so tables don't flash empty while they reload. */
  data: T | undefined;
  /** The error message if the latest request failed. */
  error: string | undefined;
  /** True while the latest request hasn't answered yet. */
  loading: boolean;
};

/**
 * Load `path` from the API, and load it again whenever `path` or `version` changes.
 *
 * - Pass `null` as the path to load nothing (for example, while waiting for another value).
 * - `version` is a number that goes up when the user presses refresh. Changing it
 *   re-runs the request even though the path is the same.
 *
 * Components normally use useApi() from SettingsProvider, which fills in `version` for them.
 */
export function useFetch<T>(path: string | null, version: number): FetchState<T> {
  // A "key" names one particular request, e.g. "/api/odds#3" (path #3 = after the third refresh).
  const key = path === null ? null : `${path}#${version}`;

  const [data, setData] = useState<T>();
  // Which request finished last, and whether it failed. Comparing its key with the
  // current key tells us if we're still waiting for the newest request.
  const [finished, setFinished] = useState<{ key: string; error?: string }>();

  useEffect(() => {
    if (path === null || key === null) return;

    // If the path changes before this request answers, React runs the cleanup function
    // below, which sets ignore = true. That way a slow, outdated answer can never
    // overwrite a newer one.
    let ignore = false;

    getJson<T>(path)
      .then((result) => {
        if (ignore) return;
        setData(result);
        setFinished({ key });
      })
      .catch((err: unknown) => {
        if (ignore) return;
        setFinished({ key, error: err instanceof Error ? err.message : String(err) });
      });

    return () => {
      ignore = true;
    };
  }, [path, key]);

  const isCurrent = finished?.key === key;
  return {
    data,
    error: isCurrent ? finished?.error : undefined,
    loading: key !== null && !isCurrent,
  };
}
