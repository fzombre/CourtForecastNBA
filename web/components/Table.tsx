// Table: one reusable table for every tab, plus small helpers for headings, captions,
// loading and error messages.
//
// Each tab describes its columns as a list of { header, cell } objects. `cell` is a
// function that receives one row and returns what to show in that column. This keeps
// every tab's table looking the same without copying <table> markup six times.
//
// The look: no box around the table. A heavier line in ink runs above the header (like a
// court's sideline), and thin lines separate the rows. Lines that mean something, like the
// playoff cut-off in the standings, are drawn heavier (see `rowRule`).

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
  /** A short description of the table for screen readers (shown visually nowhere). */
  label?: string;
};

/** The Tailwind classes for each kind of row line. Wider borders win over the thin
 *  row dividers in a collapsed table, so these show through. */
const RULE_CLASSES: Record<NonNullable<RowRule>, string> = {
  solid: "border-b-2 border-b-ink",
  dashed: "border-b-2 border-dashed border-b-ink-muted",
};

// <Row,> is a "generic": the same Table works for games, teams or anything else, and
// TypeScript still checks that each column's cell() only uses fields that Row really has.
export default function Table<Row>({ columns, rows, rowKey, maxHeight = "70vh", rowRule, label }: TableProps<Row>) {
  return (
    // overflow-auto: a table wider than a phone scrolls sideways inside this box instead of
    // making the whole page scroll sideways.
    <div className="overflow-auto border-t-2 border-ink" style={{ maxHeight }}>
      <table className="w-full border-collapse text-[15px]">
        {label && <caption className="sr-only">{label}</caption>}
        {/* sticky: in a long scrolling table the header stays at the top of the box. */}
        <thead className="sticky top-0 z-10 bg-floor">
          <tr className="border-b border-rule">
            {columns.map((column) => (
              <th
                key={column.header}
                scope="col"
                className={`px-3 pt-2.5 pb-2 text-[13px] font-medium whitespace-nowrap text-ink-muted first:pl-0 ${
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
                className={`border-b border-rule transition-colors hover:bg-floor-alt ${rule ? RULE_CLASSES[rule] : ""}`}
              >
                {columns.map((column) => (
                  <td
                    key={column.header}
                    style={column.cellStyle?.(row)}
                    className={`px-3 py-2 whitespace-nowrap first:pl-0 ${
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

/** What a tab shows before its first data arrives: an error if the request failed, otherwise "Loading...". */
export function LoadingOrError({ error, what }: { error?: string; what: string }) {
  if (error) {
    // Errors say what failed and what to do about it, without apologizing.
    return (
      <p role="alert" className="max-w-prose border-l-[3px] border-live pl-4 text-[15px]">
        Couldn&apos;t load {what}. Check that the Python API is running, then press Refresh data.
        <span className="mt-1 block text-sm text-ink-muted">{error}</span>
      </p>
    );
  }
  // aria-live: screen readers announce the message without the user having to look for it.
  return (
    <p aria-live="polite" className="animate-pulse text-ink-muted motion-reduce:animate-none">
      Loading {what}…
    </p>
  );
}

/** A small muted helper line under a heading or table, like st.caption in Streamlit. */
export function Caption({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <p className={`my-3 max-w-prose text-sm text-ink-muted ${className}`}>{children}</p>;
}

/** A note set off by a painted line on its left, like st.info in Streamlit. */
export function Info({ children }: { children: ReactNode }) {
  return <p className="max-w-prose border-l-[3px] border-paint pl-4 text-[15px]">{children}</p>;
}

/**
 * The key for the lines in the standings tables: a short sample of each line next to
 * what it means. Used on the Standings and Predicted standings tabs.
 */
export function SeedLegend() {
  return (
    <ul className="my-4 flex flex-wrap gap-x-6 gap-y-1 text-sm text-ink-muted">
      <li className="flex items-center gap-2">
        <span aria-hidden className="inline-block w-6 border-t-2 border-ink" />
        Seeds 1–6 go straight to the playoffs
      </li>
      <li className="flex items-center gap-2">
        <span aria-hidden className="inline-block w-6 border-t-2 border-dashed border-ink-muted" />
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
