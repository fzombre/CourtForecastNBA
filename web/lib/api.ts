// Small helpers for calling the Python API.
// The paths start with /api, which next.config.ts forwards to uvicorn on port 8000.
import type { Standings } from "./types";

/** GET a path from the API and return its JSON, or throw if the request failed. */
async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(path);
  if (!response.ok) {
    throw new Error(`${path} failed: ${response.status} ${response.statusText}`);
  }
  return (await response.json()) as T;
}

export const getStandings = () => getJson<Standings>("/api/standings");
