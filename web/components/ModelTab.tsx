"use client";

// Tab 6 (Model): how accurate the model has been, what it learned, and the Elo power ratings.
// Everything here comes from /api/overview, which SettingsProvider has already loaded,
// so this tab makes no request of its own.

import { useSettings } from "./SettingsProvider";
import Table, { Caption, Heading, Info, LoadingOrError, type Column } from "./Table";
import Team from "./Team";
import { pct, signed } from "@/lib/format";
import type { Accuracy, Rating } from "@/lib/types";

/** Names for the model's weights, in the same order as model.FEATURES in Python. */
const FEATURE_LABELS = ["Elo gap", "Recent margin gap", "Rest days gap"];

/** Every team starts at this Elo rating; above it means better than average. */
const AVERAGE_ELO = 1500;

// ---------- Accuracy: the model against the simplest possible guess ----------

/**
 * One horizontal bar on a 0–100% scale, with its value at the tip.
 * Bars start square at the baseline (the left edge) and have a rounded end, per the
 * chart style used across the site.
 */
function AccuracyBar({ label, value, emphasis }: { label: string; value: number; emphasis: boolean }) {
  return (
    <div className="grid grid-cols-[minmax(0,11rem)_1fr] items-center gap-4">
      <span className={`text-[15px] ${emphasis ? "font-semibold" : "text-ink-muted"}`}>{label}</span>
      <span className="flex items-center gap-3">
        {/* The track is the whole 0–100% scale; the colored part is the value. */}
        <span className="relative h-5 max-w-md flex-1">
          <span
            className={`absolute inset-y-0 left-0 rounded-r ${emphasis ? "bg-paint" : "bg-ink-muted"}`}
            style={{ width: `${value * 100}%` }}
          />
        </span>
        <span className={`w-12 tabular-nums ${emphasis ? "font-semibold" : "text-ink-muted"}`}>{pct(value)}</span>
      </span>
    </div>
  );
}

function AccuracySection({ accuracy }: { accuracy: Accuracy }) {
  // The difference in percentage points, rounded the same way the bars' labels are, so
  // the sentence always matches the numbers next to the bars.
  const gain = Math.round(accuracy.model * 100) - Math.round(accuracy.always_home * 100);
  const comparison =
    gain > 0
      ? `${gain} points better than always picking the home team`
      : gain === 0
        ? "the same as always picking the home team"
        : `${-gain} points worse than always picking the home team`;

  return (
    <section aria-labelledby="accuracy-heading">
      <Heading id="accuracy-heading" className="mb-2">
        How often it&apos;s right
      </Heading>
      <p className="mb-5 max-w-prose text-[15px]">
        The model picked the winner of <strong className="font-semibold">{pct(accuracy.model)}</strong> of the last{" "}
        {accuracy.test_games} finished games, which it never trained on. That&apos;s {comparison}.
      </p>
      {/* role="img" with a label: one sentence for screen readers instead of two loose bars.
          The numbers are also written out in the paragraph above. */}
      <div role="img" aria-label={`Model ${pct(accuracy.model)}, always home team ${pct(accuracy.always_home)}`} className="space-y-3">
        <AccuracyBar label="Model's pick" value={accuracy.model} emphasis />
        <AccuracyBar label="Always the home team" value={accuracy.always_home} emphasis={false} />
      </div>
    </section>
  );
}

// ---------- Elo: a bar growing left or right from the average ----------

/**
 * A diverging bar for one team's Elo: right of the center line (accent blue) for better
 * than average, left of it (orange) for worse. `scale` is the biggest distance from 1500
 * among all teams, so the best or worst team fills its half and the rest are in proportion.
 */
function EloBar({ elo, scale }: { elo: number; scale: number }) {
  const diff = elo - AVERAGE_ELO;
  const width = scale > 0 ? (Math.abs(diff) / scale) * 50 : 0; // percent of the whole bar
  const above = diff >= 0;
  return (
    <span aria-hidden className="relative block h-3 w-32 sm:w-44">
      {/* The center line: 1500, an average team. */}
      <span className="absolute inset-y-[-3px] left-1/2 w-px bg-ink-muted" />
      <span
        className={`absolute inset-y-0 ${above ? "left-1/2 rounded-r bg-paint" : "right-1/2 rounded-l bg-under"}`}
        style={{ width: `${width}%` }}
      />
    </span>
  );
}

export default function ModelTab() {
  const { overview } = useSettings();
  const info = overview.data;
  if (!info) return <LoadingOrError error={overview.error} what="model details" />;

  const { accuracy, weights, ratings } = info;
  // How far the farthest team is from average, for scaling the Elo bars.
  const eloScale = Math.max(0, ...ratings.map((r) => Math.abs(r.elo - AVERAGE_ELO)));

  const ratingColumns: Column<Rating>[] = [
    // Ratings arrive sorted best first, so the position is the rank.
    { header: "Rank", cell: (_r, index) => index + 1, numeric: true, className: "w-12 text-ink-muted" },
    { header: "Team", cell: (r) => <Team code={r.team} name={r.name} compact /> },
    { header: "Conf", cell: (r) => r.conference, className: "text-ink-muted" },
    { header: "Elo", cell: (r) => r.elo.toFixed(0), numeric: true },
    { header: "vs. average", cell: (r) => <EloBar elo={r.elo} scale={eloScale} /> },
    { header: "Avg margin, last 10", cell: (r) => signed(r.margin), numeric: true },
  ];

  return (
    <div className="space-y-14">
      {accuracy ? (
        <AccuracySection accuracy={accuracy} />
      ) : (
        <Info>Not enough finished games yet to test the model fairly. Accuracy shows up here once there are.</Info>
      )}

      {/* weights is null early in the season, when the app uses plain Elo instead of the trained model. */}
      {weights && (
        <section aria-labelledby="weights-heading" className="max-w-md">
          <Heading id="weights-heading" className="mb-2">
            What the model learned
          </Heading>
          <Caption>A positive weight helps the home team. A bigger weight matters more per unit.</Caption>
          <Table
            columns={[
              { header: "Feature", cell: (i: number) => FEATURE_LABELS[i] },
              { header: "Weight", cell: (i: number) => signed(weights[i], 4), numeric: true },
            ]}
            rows={weights.map((_, i) => i)} // one row per weight, identified by its position
            rowKey={(i) => String(i)}
            maxHeight="none"
            label="Model weights"
          />
        </section>
      )}

      <section aria-labelledby="ratings-heading">
        <Heading id="ratings-heading" className="mb-2">
          Power ratings
        </Heading>
        <Caption>
          Elo ratings: every team starts at {AVERAGE_ELO}, gains points for wins and loses them for losses. The bar
          shows how far above or below an average team each one is.
        </Caption>
        <Table columns={ratingColumns} rows={ratings} rowKey={(r) => r.team} label="Elo power ratings" />
      </section>
    </div>
  );
}
