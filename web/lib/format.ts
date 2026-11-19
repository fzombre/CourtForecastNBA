// Little helpers that turn numbers and dates into the text the tables show.

/** A fraction as a whole percentage: 0.643 -> "64%". Same as Python's f"{x:.0%}" in app.py. */
export function pct(fraction: number): string {
  return `${Math.round(fraction * 100)}%`;
}

/**
 * "2027-01-15" -> "Jan 15, 2027".
 *
 * We split the text ourselves instead of using new Date("2027-01-15"), because that
 * reads the text as midnight UTC, which is still Jan 14 in US time zones.
 */
export function longDate(isoDate: string): string {
  const [year, month, day] = isoDate.split("-").map(Number);
  return new Date(year, month - 1, day).toLocaleDateString("en-US", {
    month: "short",
    day: "2-digit",
    year: "numeric",
  });
}
