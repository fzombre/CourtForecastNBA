// Small helpers for calling the Python API.
//
// Every path starts with /api. The browser sends those requests to Next.js (port 3000),
// and the rewrite in next.config.ts forwards them to uvicorn (port 8000).

/** Turn a failed response into an Error with a readable message. */
async function failure(path: string, response: Response): Promise<Error> {
  // FastAPI explains what went wrong in a "detail" field; show it when there is one.
  let detail = "";
  try {
    const body = await response.json();
    detail = body?.detail ? `: ${JSON.stringify(body.detail)}` : "";
  } catch {
    // The body wasn't JSON (for example, the Python API isn't running). Use the status alone.
  }
  return new Error(`${path} failed (${response.status} ${response.statusText})${detail}`);
}

/**
 * GET a path from the API and return its JSON.
 *
 * The <T> is a "type parameter": the caller says what shape it expects back,
 * e.g. getJson<Standings>("/api/standings"), and TypeScript checks every use of the result.
 */
export async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(path);
  if (!response.ok) throw await failure(path, response);
  return (await response.json()) as T;
}

/** POST to a path (used by the refresh button) and return its JSON. */
export async function postJson<T>(path: string): Promise<T> {
  const response = await fetch(path, { method: "POST" });
  if (!response.ok) throw await failure(path, response);
  return (await response.json()) as T;
}
