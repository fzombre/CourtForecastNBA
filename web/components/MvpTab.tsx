"use client";

// The MVP race tab: who's likely to win MVP, and who would win if the season ended today.
// Everything comes from /api/mvp, which runs src/mvp.py.
//
// From top to bottom:
//   1. The favorite: the player with the best chance to win, with the next two beside him
//      (the same framed strip as the title favorite on Playoff odds).
//   2. "Chance to win MVP": the prediction. One bar per contender, on a 0–100% scale.
//   3. "The ladder today": the ranking. If the season ended today, who would the model
//      pick? With each player's stats, so you can see why.
//   4. "How it decides": how often the model found the real MVP in past seasons, and how
//      much each stat counts.
//
// Two different numbers, on purpose: the ladder reads today's stats as final; the chance
// to win also plays out the rest of the season (injuries, the 65-game rule, team records,
// hot starts cooling off). In November they can be far apart; by April they agree.

import { useSettings, useApi } from "./SettingsProvider";
import Table, { Caption, Heading, Info, LoadingOrError, type Column } from "./Table";
import PlayerPhoto from "./PlayerPhoto";
import Team, { TeamLogo } from "./Team";
import { signed } from "@/lib/format";
import type { MvpCandidate, MvpFeature, MvpRace } from "@/lib/types";

/** How many contenders get a bar in "Chance to win MVP": the top 5, the real contenders. */
const CHANCE_ROWS = 5;

/**
 * How many places the ladder shows: the top 5. The API sends more than that (the top 15
 * of the ladder, MVP_LADDER_SIZE in src/api.py, plus anyone further down who still has a
 * real chance to win), so the cut is made here. Filtering on rank, not just taking the
 * first rows, also keeps the ladder free of gaps (1, 2, 3, 4, 5, never 1, 2, 3, 18...).
 */
const LADDER_ROWS = 5;

/** Plain names for the six numbers the model weighs, in the order the API sends them. */
const FEATURE_LABELS: Record<MvpFeature, string> = {
  pts: "Points",
  reb: "Rebounds",
  ast: "Assists",
  ts_pct: "True shooting %",
  plus_minus: "Plus/minus",
  win_pct: "Team win %",
};

/**
 * A chance in percent, written so tiny and near-certain values stay honest:
 *   56.35 -> "56.4%",  0.01 -> "<0.1%",  99.99 -> ">99.9%".
 * (Rounding 0.01 to "0.0%" would claim "no chance"; he still has a sliver.)
 */
function chance(value: number): string {
  if (value < 0.05) return "<0.1%";
  if (value >= 99.95) return ">99.9%";
  return `${value.toFixed(1)}%`;
}

/** A fraction as a percentage with one decimal: 0.627 -> "62.7%". For true shooting. */
function fractionPct(fraction: number): string {
  return `${(fraction * 100).toFixed(1)}%`;
}

/** "Luka Dončić · LAL" style second line: his team's logo and code, quiet. */
function TeamLine({ code }: { code: string }) {
  return (
    <span className="inline-flex items-center gap-1.5 text-sm text-muted">
      <TeamLogo code={code} size={16} />
      {code}
    </span>
  );
}

// ---------- 1. The favorite ----------

function Favorite({ player }: { player: MvpCandidate }) {
  const { teamName } = useSettings();
  return (
    <div className="flex min-w-0 items-center gap-5">
      <PlayerPhoto playerId={player.player_id} name={player.name} size={88} />
      <div className="min-w-0">
        <p className="text-sm text-muted">MVP favorite</p>
        {/* break-words: a long name ("Shai Gilgeous-Alexander") wraps instead of
            pushing the page sideways on a phone. */}
        <p className="font-display text-4xl leading-none font-extrabold tracking-tight break-words sm:text-5xl">
          {player.name}
        </p>
        <p className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-[15px]">
          <span>
            <strong className="font-semibold text-pick">{chance(player.chance)}</strong> chance to win MVP
          </span>
          <span className="inline-flex items-center gap-1.5 text-muted">
            <TeamLogo code={player.team} size={18} />
            {teamName(player.team)}
          </span>
        </p>
      </div>
    </div>
  );
}

// ---------- 2. Chance to win MVP ----------

/**
 * One contender's bar. The track is the whole 0–100% scale, so a 56% favorite fills a
 * bit over half: the length is the chance itself, not "compared with the leader".
 * The favorite's bar is gold (the model's pick, like the picks on Upcoming); the rest
 * are periwinkle, the site's color for amounts.
 */
function ChanceRow({ player, place, favorite }: { player: MvpCandidate; place: number; favorite: boolean }) {
  return (
    <li className="grid grid-cols-[1.5rem_2.5rem_minmax(0,1fr)_4.5rem] items-center gap-x-3 py-2.5">
      <span className="text-right text-sm text-muted tabular-nums">{place}</span>
      <PlayerPhoto playerId={player.player_id} name={player.name} size={40} />
      <span className="min-w-0">
        <span className="flex flex-wrap items-center gap-x-2">
          <span className={`truncate text-[15px] ${favorite ? "font-semibold" : ""}`}>{player.name}</span>
          <TeamLine code={player.team} />
        </span>
        {/* The bar sits under the name, so the row works the same on a phone and a
            desktop. aria-hidden: the percentage at the end of the row says the same. */}
        <span aria-hidden className="relative mt-1.5 block h-2 rounded-r bg-track/50">
          <span
            className={`absolute inset-y-0 left-0 rounded-r ${favorite ? "bg-pick" : "bg-metric"}`}
            // At least 2px, so a 0.3% chance still shows a sliver instead of nothing.
            style={{ width: `max(2px, ${Math.min(100, player.chance)}%)` }}
          />
        </span>
      </span>
      <span className={`text-right text-[15px] tabular-nums ${favorite ? "font-semibold text-pick" : ""}`}>
        {chance(player.chance)}
      </span>
    </li>
  );
}

function ChanceSection({ race }: { race: MvpRace }) {
  const contenders = race.candidates.slice(0, CHANCE_ROWS);
  return (
    <section aria-labelledby="chance-heading">
      <Heading id="chance-heading" className="mb-2">
        Chance to win MVP
      </Heading>
      <Caption>
        From {race.n_sims.toLocaleString()} simulated rests of the season. Each one plays out every contender&apos;s
        games: how many he misses, whether he reaches the {race.games_required} games the NBA requires, his
        team&apos;s record, and how his numbers settle as hot starts cool off.
      </Caption>
      <ol aria-label="Chance to win MVP" className="max-w-2xl divide-y divide-line">
        {contenders.map((player, i) => (
          <ChanceRow key={player.player_id} player={player} place={i + 1} favorite={i === 0} />
        ))}
      </ol>
    </section>
  );
}

// ---------- 3. The ladder today ----------

const LADDER_COLUMNS: Column<MvpCandidate>[] = [
  { header: "Rank", cell: (p) => p.rank, numeric: true, className: "w-12 text-muted" },
  {
    header: "Player",
    cell: (p) => (
      <span className="inline-flex items-center gap-2.5">
        <PlayerPhoto playerId={p.player_id} name={p.name} size={28} />
        {p.name}
      </span>
    ),
  },
  // compact: the three-letter code on phones, the full team name from `sm` up.
  { header: "Team", cell: (p) => <Team code={p.team} compact /> },
  { header: "GP", cell: (p) => p.gp, numeric: true },
  { header: "PTS", cell: (p) => p.pts.toFixed(1), numeric: true },
  { header: "REB", cell: (p) => p.reb.toFixed(1), numeric: true },
  { header: "AST", cell: (p) => p.ast.toFixed(1), numeric: true },
  { header: "TS%", cell: (p) => fractionPct(p.ts_pct), numeric: true },
  { header: "+/−", cell: (p) => signed(p.plus_minus), numeric: true },
  // His team's record in the games he played (not the team's whole record).
  { header: "Record", cell: (p) => `${p.w}–${p.l}`, numeric: true },
  { header: "If it ended today", cell: (p) => chance(p.today), numeric: true, className: "font-semibold" },
  { header: "To win", cell: (p) => chance(p.chance), numeric: true, className: "text-muted" },
];

function LadderSection({ race }: { race: MvpRace }) {
  // The API sends candidates by chance to win; the ladder is by today's rank instead.
  // Players without a rank aren't on track for the games rule, so they sit out the ladder.
  const ranked = race.candidates
    .filter((p): p is MvpCandidate & { rank: number } => p.rank !== null && p.rank <= LADDER_ROWS)
    .sort((a, b) => a.rank - b.rank);
  // Contenders for the award who aren't on the ladder today: worth a sentence, because
  // otherwise "why is he in the chart above but not in the ladder?" has no answer.
  const sittingOut = race.candidates.slice(0, CHANCE_ROWS).filter((p) => p.rank === null);

  return (
    <section aria-labelledby="ladder-heading">
      <Heading id="ladder-heading" className="mb-2">
        The ladder today
      </Heading>
      <Caption>
        If the season ended today, the model&apos;s pick, with today&apos;s numbers taken as final. Only players on
        pace for {race.games_required} of {race.season_games} games are ranked. Record is his team&apos;s record in the
        games he played.
        {sittingOut.length > 0 && (
          <>
            {" "}
            Not ranked yet, having missed too many of their team&apos;s games so far:{" "}
            {sittingOut.map((p) => `${p.name} (${p.gp} of ${p.team_gp})`).join(", ")}.
          </>
        )}
      </Caption>
      {ranked.length > 0 ? (
        <Table
          columns={LADDER_COLUMNS}
          rows={ranked}
          rowKey={(p) => String(p.player_id)}
          maxHeight="none"
          label="MVP ladder: if the season ended today"
        />
      ) : (
        <Info>Nobody has played enough games yet to be ranked. The ladder fills in after the first few games.</Info>
      )}
    </section>
  );
}

// ---------- 4. How it decides ----------

/** One stat's weight as a bar, scaled so the heaviest weight fills the track. */
function WeightRow({ label, weight, scale }: { label: string; weight: number; scale: number }) {
  return (
    // The bar column stops at 24rem, so each number sits right at the end of its bar's
    // track instead of drifting to the far side of a wide screen.
    <div className="grid grid-cols-[minmax(0,9.5rem)_minmax(0,24rem)_3rem] items-center gap-3">
      <span className="text-[15px]">{label}</span>
      <span aria-hidden className="relative h-3 rounded-r bg-track/50">
        <span
          className="absolute inset-y-0 left-0 rounded-r bg-metric"
          style={{ width: `${scale > 0 ? (Math.max(0, weight) / scale) * 100 : 0}%` }}
        />
      </span>
      <span className="text-right text-sm text-muted tabular-nums">{weight.toFixed(2)}</span>
    </div>
  );
}

function HowSection({ race }: { race: MvpRace }) {
  const { backtest, weights } = race;
  // Heaviest first, so the chart reads as a ranking of what matters most.
  const sorted = [...weights].sort((a, b) => b.weight - a.weight);
  const scale = Math.max(0, ...weights.map((w) => w.weight));

  return (
    <section aria-labelledby="how-heading">
      <Heading id="how-heading" className="mb-2">
        How it decides
      </Heading>
      <p className="mb-5 max-w-prose text-[15px]">
        The model learned from every MVP vote from {backtest.first_season} to {backtest.last_season}. Tested on each
        of those {backtest.seasons} seasons with that season hidden from training, it picked the real MVP{" "}
        <strong className="font-semibold">{backtest.top1}</strong> times, and had him in its top three{" "}
        <strong className="font-semibold">{backtest.top3}</strong> times. The misses were mostly close races, where
        voters went with the story of the season over the numbers.
      </p>
      <Caption>
        How much each stat moves a player&apos;s score, for one standard deviation above the average contender.
      </Caption>
      {/* role="img" + label: one sentence for screen readers instead of six loose bars;
          the numbers are also written at the end of each row. */}
      <div
        role="img"
        aria-label={`Weights: ${sorted.map((w) => `${FEATURE_LABELS[w.feature]} ${w.weight.toFixed(2)}`).join(", ")}`}
        className="space-y-2.5"
      >
        {sorted.map((w) => (
          <WeightRow key={w.feature} label={FEATURE_LABELS[w.feature]} weight={w.weight} scale={scale} />
        ))}
      </div>
    </section>
  );
}

// ---------- The tab ----------

export default function MvpTab() {
  const { data: race, error, loading } = useApi<MvpRace>("/api/mvp");

  // The first visit downloads player stats and runs the season simulation: a few seconds.
  if (!race) return <LoadingOrError error={error} what="the MVP race (this takes a few seconds)" rows={10} />;

  if (race.candidates.length === 0) {
    return <Info>The season hasn&apos;t started yet. The MVP race appears after the first games.</Info>;
  }

  const [favorite, ...rest] = race.candidates;
  const nextInLine = rest.slice(0, 2);

  return (
    <div className="space-y-14">
      {/* The one framed strip on this page: the answer to "who's going to win MVP?" */}
      <div className="flex flex-wrap items-center justify-between gap-x-10 gap-y-6 rounded-2xl border border-line bg-panel p-5 md:p-6">
        <Favorite player={favorite} />
        {nextInLine.length > 0 && (
          <div>
            <p className="mb-2 text-sm text-muted">Next in line</p>
            <ol className="space-y-2">
              {nextInLine.map((p) => (
                <li key={p.player_id} className="flex items-center justify-between gap-6 text-[15px]">
                  <span className="inline-flex items-center gap-2">
                    <PlayerPhoto playerId={p.player_id} name={p.name} size={24} />
                    {p.name}
                  </span>
                  <span className="tabular-nums">{chance(p.chance)}</span>
                </li>
              ))}
            </ol>
          </div>
        )}
      </div>

      <ChanceSection race={race} />
      <LadderSection race={race} />
      <HowSection race={race} />

      <Caption>
        Player stats: {race.source.startsWith("live") ? "live from NBA.com" : `the ${race.source}`}, {race.season}{" "}
        regular season.
        {loading && " Updating…"}
      </Caption>
    </div>
  );
}
