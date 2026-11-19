// Table: one reusable table for every tab, plus small helpers for loading and error messages.
//
// Each tab describes its columns as a list of { header, cell } objects. `cell` is a
// function that receives one row and returns what to show in that column. This keeps
// every tab's table looking the same without copying <table> markup six times.

import type { ReactNode } from "react";

export type Column<Row> = {
  header: string;
  cell: (row: Row, index: number) => ReactNode;
  /** Right-align the column, which makes numbers easier to compare. */
  numeric?: boolean;
};

type TableProps<Row> = {
  columns: Column<Row>[];
  rows: Row[];
  /** A unique id for each row (React needs one to update long lists efficiently). */
  rowKey: (row: Row) => string;
  /** Long tables scroll inside their own box, with the header row staying visible. */
  maxHeight?: string;
};

// <Row,> is a "generic": the same Table works for games, teams or anything else, and
// TypeScript still checks that each column's cell() only uses fields that Row really has.
export default function Table<Row>({ columns, rows, rowKey, maxHeight = "70vh" }: TableProps<Row>) {
  return (
    <div className="overflow-auto rounded-lg border border-zinc-200 dark:border-zinc-800" style={{ maxHeight }}>
      <table className="w-full border-collapse text-sm">
        <thead className="sticky top-0 bg-zinc-100 dark:bg-zinc-900">
          <tr>
            {columns.map((column) => (
              <th
                key={column.header}
                className={`whitespace-nowrap px-3 py-2 font-semibold ${column.numeric ? "text-right" : "text-left"}`}
              >
                {column.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={rowKey(row)} className="border-t border-zinc-200 dark:border-zinc-800">
              {columns.map((column) => (
                <td
                  key={column.header}
                  className={`whitespace-nowrap px-3 py-1.5 ${column.numeric ? "text-right tabular-nums" : ""}`}
                >
                  {column.cell(row, index)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** What a tab shows before its first data arrives: an error if the request failed, otherwise "Loading...". */
export function LoadingOrError({ error, what }: { error?: string; what: string }) {
  if (error) {
    return (
      <p className="rounded-lg bg-red-50 p-3 text-red-700 dark:bg-red-950 dark:text-red-300">
        Could not load {what}. Is the Python API running? ({error})
      </p>
    );
  }
  return <p className="text-zinc-500">Loading {what}...</p>;
}

/** A grey helper line under a heading or table, like st.caption in Streamlit. */
export function Caption({ children }: { children: ReactNode }) {
  return <p className="my-2 text-sm text-zinc-500">{children}</p>;
}

/** A blue information box, like st.info in Streamlit. */
export function Info({ children }: { children: ReactNode }) {
  return <p className="rounded-lg bg-blue-50 p-3 text-blue-800 dark:bg-blue-950 dark:text-blue-200">{children}</p>;
}
