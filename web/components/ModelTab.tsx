"use client";

// Tab 6 (Model): how accurate the model has been, what it learned, and the Elo power ratings.
// Everything here comes from /api/overview, which SettingsProvider has already loaded,
// so this tab makes no request of its own.

import { useSettings } from "./SettingsProvider";
import Table, { Caption, Info, LoadingOrError, type Column } from "./Table";
import { pct } from "@/lib/format";
import type { Rating } from "@/lib/types";

/** Names for the model's weights, in the same order as model.FEATURES in Python. */
const FEATURE_LABELS = ["Elo gap", "Recent margin gap", "Rest days gap"];

const RATING_COLUMNS: Column<Rating>[] = [
  { header: "Team", cell: (r) => r.name },
  { header: "Conf", cell: (r) => r.conference },
  { header: "Elo", cell: (r) => r.elo.toFixed(1), numeric: true },
  { header: "Avg margin (last 10)", cell: (r) => r.margin.toFixed(1), numeric: true },
];

/** A big number with a label above it, like st.metric in Streamlit. */
function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-sm text-zinc-500">{label}</p>
      <p className="text-3xl font-semibold">{value}</p>
    </div>
  );
}

export default function ModelTab() {
  const { overview } = useSettings();
  const info = overview.data;
  if (!info) return <LoadingOrError error={overview.error} what="model details" />;

  const { accuracy, weights } = info;

  return (
    <section className="space-y-8">
      <div>
        {accuracy ? (
          <>
            <div className="grid max-w-xl grid-cols-2 gap-4">
              <Metric label="Model picked the winner" value={pct(accuracy.model)} />
              <Metric label="Always picking the home team" value={pct(accuracy.always_home)} />
            </div>
            <Caption>Tested on the last {accuracy.test_games} finished games, which the model didn&apos;t train on.</Caption>
          </>
        ) : (
          <Info>Not enough finished games yet to test the model fairly.</Info>
        )}
      </div>

      {/* weights is null early in the season, when the app uses plain Elo instead of the trained model. */}
      {weights && (
        <div className="max-w-md">
          <h2 className="mb-1 text-xl font-semibold">What the model learned</h2>
          <Caption>Positive weight = helps the home team. Bigger = matters more per unit.</Caption>
          <Table
            columns={[
              { header: "Feature", cell: (i: number) => FEATURE_LABELS[i] },
              { header: "Weight", cell: (i: number) => weights[i].toFixed(4), numeric: true },
            ]}
            rows={weights.map((_, i) => i)} // one row per weight, identified by its position
            rowKey={(i) => String(i)}
            maxHeight="none"
          />
        </div>
      )}

      <div>
        <h2 className="mb-2 text-xl font-semibold">Power ratings (Elo)</h2>
        <Table columns={RATING_COLUMNS} rows={info.ratings} rowKey={(r) => r.team} />
      </div>
    </section>
  );
}
