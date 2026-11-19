// Little helpers that turn numbers and dates into the text the tables show.

/** A fraction as a whole percentage: 0.643 -> "64%". Same as Python's f"{x:.0%}" in app.py. */
export function pct(fraction: number): string {
  return `${Math.round(fraction * 100)}%`;
}

/** A win percentage the way standings print it: 0.812 -> ".812", 1 -> "1.000". */
export function winPct(fraction: number): string {
  return fraction.toFixed(3).replace(/^0/, "");
}

/** Games behind, with the leader shown as a dash instead of "0": 0 -> "—", 3.5 -> "3.5". */
export function gamesBehind(gb: number): string {
  return gb === 0 ? "—" : gb.toFixed(1);
}

/** A percentage the API already sends as a number of percent, with one decimal: 20.4 -> "20.4%". */
export function percent(value: number): string {
  return `${value.toFixed(1)}%`;
}

/** A number with an explicit sign, for values above/below zero: 4.21 -> "+4.2", -1 -> "−1.0". */
export function signed(value: number, digits = 1): string {
  const text = Math.abs(value).toFixed(digits);
  // A real minus sign (−), not a hyphen (-): it's the same width as "+", so columns line up.
  if (Number(text) === 0) return text;
  return value > 0 ? `+${text}` : `−${text}`;
}

/** "2026-11-18" -> a local Date at midnight on that day (see longDate for why we split it). */
function localDay(isoDate: string): Date {
  const [year, month, day] = isoDate.split("-").map(Number);
  return new Date(year, month - 1, day);
}

/**
 * The heading for a day of games:
 *   today     -> "Today"
 *   tomorrow  -> "Tomorrow"
 *   yesterday -> "Yesterday"
 *   otherwise -> "Thursday, Nov 19"
 * Plus a second, quieter part with the date, so "Today" still tells you which day it is.
 */
export function dayHeading(isoDate: string): { main: string; detail: string } {
  const day = localDay(isoDate);
  const today = new Date();
  today.setHours(0, 0, 0, 0); // midnight today, so we compare whole days
  // Math.round handles the 23- and 25-hour days when clocks change.
  const daysAway = Math.round((day.getTime() - today.getTime()) / 86_400_000);

  const weekday = day.toLocaleDateString("en-US", { weekday: "long" });
  const date = day.toLocaleDateString("en-US", { month: "short", day: "numeric" });
  // Only show the year when it isn't this year (e.g. a game in January seen in November).
  const year = day.getFullYear() !== today.getFullYear() ? `, ${day.getFullYear()}` : "";

  const relative: Record<number, string> = { [-1]: "Yesterday", 0: "Today", 1: "Tomorrow" };
  if (daysAway in relative) return { main: relative[daysAway], detail: `${weekday}, ${date}${year}` };
  return { main: weekday, detail: `${date}${year}` };
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
