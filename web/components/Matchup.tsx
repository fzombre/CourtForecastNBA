"use client";

// Matchup: one upcoming (or live) game as a single row:
//
//      7:30 pm ET     Boston Celtics [logo]  46%  [======|=========]  54%  [logo] Denver Nuggets
//                                                        ^ the 50% line
//
// The bar in the middle is the main picture of the Upcoming tab. It's one whole split in
// two: the left part is the away team's chance to win, the right part the home team's.
// The predicted winner's part is lit in gold (the "court light") and the other part is a
// dark slate track, so down a list of games you can see at a glance who's favored and by how much.
// The small tick in the middle marks 50%, like the half-court line: the further the
// gold part crosses it, the more lopsided the game.
//
// The layout (named grid areas, and the phone version) lives in globals.css under .matchup.

import Team from "./Team";
import { pct } from "@/lib/format";
import type { UpcomingGame } from "@/lib/types";

/**
 * The split bar. `homeChance` is the home team's chance to win, between 0 and 1.
 * role="img" + aria-label: screen readers read the label instead of trying to describe
 * empty boxes. title= gives the same text as a tooltip on hover.
 */
function SplitBar({ homeChance, description }: { homeChance: number; description: string }) {
  const homeFavored = homeChance >= 0.5;
  // The parts' widths in percent. The favorite's part animates out from 50% when the
  // tab loads (the .lean class in globals.css); the other part takes whatever is left.
  const awayWidth = `${(1 - homeChance) * 100}%`;
  const homeWidth = `${homeChance * 100}%`;

  return (
    <div role="img" aria-label={description} title={description} className="relative py-1.5" style={{ gridArea: "bar" }}>
      {/* gap-0.5: a 2px gap between the two parts, so they read as two pieces of one whole. */}
      <div className="flex h-2 gap-0.5">
        <div
          className={`rounded-l-full ${homeFavored ? "flex-1 bg-track" : "lean bg-pick"}`}
          style={homeFavored ? undefined : { flexBasis: awayWidth }}
        />
        <div
          className={`rounded-r-full ${homeFavored ? "lean bg-pick" : "flex-1 bg-track"}`}
          style={homeFavored ? { flexBasis: homeWidth } : undefined}
        />
      </div>
      {/* The 50% tick: a thin line in the text color, a little taller than the bar, centered. */}
      <span aria-hidden className="absolute inset-y-0 left-1/2 w-px -translate-x-1/2 bg-fg/70" />
    </div>
  );
}

/** One team's chance, set bold when that team is the predicted winner. */
function Chance({ value, picked, area }: { value: number; picked: boolean; area: "ap" | "hp" }) {
  return (
    <span
      className={`tabular-nums ${area === "ap" ? "text-right" : "text-left"} ${
        picked ? "font-semibold text-fg" : "text-muted"
      }`}
      style={{ gridArea: area }}
    >
      {pct(value)}
    </span>
  );
}

export default function Matchup({ game }: { game: UpcomingGame }) {
  const live = game.status === 2; // 2 = being played right now
  // Scores only mean something once points are on the board. The schedule feed can report
  // 0-0 for a game already at halftime (its live scores lag), and showing "0 0" there
  // would be wrong, so a live 0-0 shows just the period.
  const showScore = live && game.away_score + game.home_score > 0;
  const homeChance = game.home_win_prob;
  const homePicked = game.predicted_winner === game.home;
  const pickName = homePicked ? game.home_name : game.away_name;
  const description = `${pickName} ${pct(game.confidence)} to win`;

  return (
    <div className="matchup">
      {/* Start time, or for a live game a red badge with the period ("3rd Qtr"). */}
      <span style={{ gridArea: "time" }} className="text-sm whitespace-nowrap text-muted tabular-nums">
        {live ? (
          <span className="inline-flex h-6 items-center gap-1.5 rounded-full bg-live/15 px-2.5 text-[13px] font-semibold text-live">
            {/* A softly pulsing dot says "this is happening now"; it stays still for reduced motion. */}
            <span aria-hidden className="size-1.5 animate-pulse rounded-full bg-live motion-reduce:animate-none" />
            <span>
              <span className="sr-only">Live, </span>
              {game.status_text}
            </span>
          </span>
        ) : (
          game.status_text
        )}
        {/* Most games are regular season; only mention the type when it's something else. */}
        {game.stage !== "Regular Season" && <span className="ml-2 text-muted md:ml-0 md:block">{game.stage}</span>}
      </span>

      <span style={{ gridArea: "away" }} className={`flex justify-end text-right ${!homePicked ? "font-semibold" : ""}`}>
        <Team code={game.away} name={game.away_name} compact logoAfter />
        {showScore && <span className="ml-2 tabular-nums">{game.away_score}</span>}
      </span>
      <Chance value={1 - homeChance} picked={!homePicked} area="ap" />

      <SplitBar homeChance={homeChance} description={description} />

      <Chance value={homeChance} picked={homePicked} area="hp" />
      <span style={{ gridArea: "home" }} className={`flex ${homePicked ? "font-semibold" : ""}`}>
        {showScore && <span className="mr-2 tabular-nums">{game.home_score}</span>}
        <Team code={game.home} name={game.home_name} compact />
      </span>
    </div>
  );
}
