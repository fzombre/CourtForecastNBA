// Table: one reusable table for every tab, plus the small pieces every tab shares:
// the page title (PageIntro), section headings, loading skeletons, notices and captions.
//
// Each tab describes its columns as a list of { header, cell } objects. `cell` is a
// function that receives one row and returns what to show in that column. This keeps
// every tab's table looking the same without copying <table> markup six times.
//
// The look: a table is an object you read, so it sits in a panel (one step lighter than
// the page) with rounded corners. Thin lines separate the rows. Lines that mean something,
// like the playoff cut-off in the standings, are drawn heavier (see `rowRule`).

import type { CSSProperties, ReactNode } from "react";

export type Column<Row> = {
  header: string;
  cell: (row: Row, index: number) => ReactNode;
  /** Right-align the column with equal-width digits, which makes numbers easier to compare. */
  numeric?: boolean;
  /** Extra inline style for one cell, e.g. a background shade that depends on the value. */
  cellStyle?: (row: Row) => CSSProperties | undefined;
  /** Extra classes for the column's cells (and header), e.g. a fixed width. */
  className?: string;
};

/**
 * A meaningful line under a row:
 *  - "solid":  a heavy line, e.g. under seed 6, the last team that goes straight to the playoffs
 *  - "dashed": a heavy dashed line, e.g. under seed 10, the last team in the play-in
 */
export type RowRule = "solid" | "dashed" | undefined;

type TableProps<Row> = {
  columns: Column<Row>[];
  rows: Row[];
  /** A unique id for each row (React needs one to update long lists efficiently). */
  rowKey: (row: Row) => string;
  /** Long tables scroll inside their own box, with the header row staying visible. */
  maxHeight?: string;
  /** Which line (if any) to draw under the row at `index`. */
  rowRule?: (index: number) => RowRule;
  /** A short description of the table for screen readers (not shown on screen). */
  label?: string;
};

/** The Tailwind classes for each kind of row line. In a collapsed table the wider border
 *  wins over the thin row divider, so these show through. */
const RULE_CLASSES: Record<NonNullable<RowRule>, string> = {
  solid: "border-b-2 border-b-muted/70",
  dashed: "border-b-2 border-dashed border-b-muted/50",
};

// <Row,> is a "generic": the same Table works for games, teams or anything else, and
// TypeScript still checks that each column's cell() only uses fields that Row really has.
export default function Table<Row>({ columns, rows, rowKey, maxHeight = "70vh", rowRule, label }: TableProps<Row>) {
  return (
    // overflow-auto: a table wider than a phone scrolls sideways inside this panel instead
    // of making the whole page scroll sideways.
    <div className="overflow-auto rounded-xl border border-line bg-panel" style={{ maxHeight }}>
      <table className="w-full border-collapse text-[15px]">
        {label && <caption className="sr-only">{label}</caption>}
        {/* sticky: in a long scrolling table the header stays at the top of the panel. */}
        <thead className="sticky top-0 z-10 bg-panel">
          <tr className="border-b border-line-strong">
            {columns.map((column) => (
              <th
                key={column.header}
                scope="col"
                className={`px-3 pt-3 pb-2.5 text-[13px] font-medium whitespace-nowrap text-muted first:pl-4 last:pr-4 ${
                  column.numeric ? "text-right" : "text-left"
                } ${column.className ?? ""}`}
              >
                {column.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => {
            const rule = rowRule?.(index);
            return (
              <tr
                key={rowKey(row)}
                className={`border-b border-line transition-colors last:border-b-0 hover:bg-raised/70 ${
                  rule ? RULE_CLASSES[rule] : ""
                }`}
              >
                {columns.map((column) => (
                  <td
                    key={column.header}
                    style={column.cellStyle?.(row)}
                    className={`px-3 py-2.5 whitespace-nowrap first:pl-4 last:pr-4 ${
                      column.numeric ? "text-right tabular-nums" : ""
                    } ${column.className ?? ""}`}
                  >
                    {column.cell(row, index)}
                  </td>
                ))}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

/**
 * The top of every tab: a large title in the display face and one plain sentence saying
 * what the page shows. Rendered by the app/.../page.tsx files, outside the tab component,
 * so it's on screen right away while the tab's data is still loading.
 */
export function PageIntro({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="mb-10">
      <h1 className="font-display text-5xl leading-[0.95] font-extrabold tracking-tight sm:text-6xl">{title}</h1>
      <p className="mt-3 max-w-prose text-[15px] text-muted">{children}</p>
    </div>
  );
}

/**
 * A section title in the display face, e.g. "East" or "Power ratings".
 * `id` lets a <section aria-labelledby="..."> take its name from this heading.
 */
export function Heading({ children, className = "", id }: { children: ReactNode; className?: string; id?: string }) {
  return (
    <h2 id={id} className={`font-display text-3xl leading-none font-bold tracking-tight ${className}`}>
      {children}
    </h2>
  );
}

/**
 * What a tab shows before its first data arrives.
 *  - If the request failed: what failed and what to do about it (no apologies).
 *  - Otherwise: a short line saying what's loading, and grey placeholder rows shaped like
 *    the content that's coming, so the page doesn't jump when the data lands.
 */
export function LoadingOrError({ error, what, rows = 8 }: { error?: string; what: string; rows?: number }) {
  if (error) {
    return (
      <div role="alert" className="max-w-prose rounded-xl border border-live/40 bg-live/10 px-4 py-3 text-[15px]">
        <p>Couldn&apos;t load {what}. Check that the Python API is running, then press refresh (top right).</p>
        <p className="mt-1 text-sm break-words text-muted">{error}</p>
      </div>
    );
  }
  return (
    // aria-busy + the polite live region: screen readers say "Loading ..." once, and the
    // placeholder bars themselves are hidden from them.
    <div aria-busy="true">
      <p aria-live="polite" className="mb-4 text-sm text-muted">
        Loading {what}…
      </p>
      <div aria-hidden className="overflow-hidden rounded-xl border border-line bg-panel">
        {Array.from({ length: rows }, (_, i) => (
          <div key={i} className="flex items-center gap-4 border-b border-line px-4 py-3.5 last:border-b-0">
            <span className="size-5 shrink-0 animate-pulse rounded-full bg-raised motion-reduce:animate-none" />
            {/* Varying widths (a fixed pattern, not random) so the rows look like text. */}
            <span
              className="h-3 animate-pulse rounded bg-raised motion-reduce:animate-none"
              style={{ width: `${[38, 52, 30, 46, 58, 34, 44, 50][i % 8]}%` }}
            />
            <span className="ml-auto h-3 w-12 animate-pulse rounded bg-raised motion-reduce:animate-none" />
          </div>
        ))}
      </div>
    </div>
  );
}

/** A small muted helper line under a heading or table, like st.caption in Streamlit. */
export function Caption({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <p className={`my-3 max-w-prose text-sm text-muted ${className}`}>{children}</p>;
}

/** A short notice in its own panel, like st.info in Streamlit (e.g. "No games left"). */
export function Info({ children }: { children: ReactNode }) {
  return (
    <p className="max-w-prose rounded-xl border border-line bg-panel px-4 py-3 text-[15px] text-fg/90">{children}</p>
  );
}

/**
 * The key for the lines in the standings tables: a short sample of each line next to
 * what it means. Used on the Standings and Predicted standings tabs.
 */
export function SeedLegend() {
  return (
    <ul className="mb-6 flex flex-wrap gap-x-6 gap-y-1 text-sm text-muted">
      <li className="flex items-center gap-2">
        <span aria-hidden className="inline-block w-6 border-t-2 border-muted/70" />
        Seeds 1–6 go straight to the playoffs
      </li>
      <li className="flex items-center gap-2">
        <span aria-hidden className="inline-block w-6 border-t-2 border-dashed border-muted/50" />
        Seeds 7–10 play in the play-in tournament
      </li>
    </ul>
  );
}

/** The standings line rule: a solid line under the 6th seed and a dashed one under the 10th. */
export function seedRule(index: number): RowRule {
  if (index === 5) return "solid"; // index 5 = the 6th team (indexes start at 0)
  if (index === 9) return "dashed"; // index 9 = the 10th team
  return undefined;
}
