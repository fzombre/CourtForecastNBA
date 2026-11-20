"use client";

// GameDays: a long list of games split into days ("Today", "Tomorrow", "Friday, Nov 20"),
// showing a few days at a time with a button to load more.
//
// Used by Results (newest day first) and Upcoming (soonest day first). Both lists can hold
// close to a thousand games; drawing them all at once would make the page slow and endless
// to scroll, and almost nobody needs more than the next or last few days.
//
// Each day's heading sticks to the top of the screen (just under the top bar) while you
// scroll through that day's games, so you always know which day you're looking at.
//
// To start over from the first days when a filter changes, the parent gives this component
// a `key` that changes with the filter: React then throws away the old list (and its
// "how many days are shown" count) and makes a fresh one.

import { useState, type ReactNode } from "react";
import { groupByDate } from "@/lib/group";
import { dayHeading } from "@/lib/format";

type GameDaysProps<Game> = {
  games: Game[];
  /** Draws one game. Returned inside an <li>, so it shouldn't add its own list item. */
  renderGame: (game: Game) => ReactNode;
  gameKey: (game: Game) => string;
  /** How many days to show at first, and how many more each press of the button adds. */
  daysPerPage?: number;
  /** Shown instead of the list when there are no games at all (e.g. a filter matches nothing). */
  empty: ReactNode;
};

export default function GameDays<Game extends { date: string }>({
  games,
  renderGame,
  gameKey,
  daysPerPage = 4,
  empty,
}: GameDaysProps<Game>) {
  const [shownDays, setShownDays] = useState(daysPerPage);

  if (games.length === 0) return <>{empty}</>;

  const days = groupByDate(games);
  const remaining = days.length - shownDays;
  const next = Math.min(daysPerPage, remaining); // how many days the button adds

  return (
    <div className="space-y-10">
      {days.slice(0, shownDays).map(([date, dayGames]) => {
        const heading = dayHeading(date);
        return (
          // aria-labelledby names each day's section after its heading, so screen reader
          // users can jump between days.
          <section key={date} aria-labelledby={`day-${date}`}>
            {/* The sticky heading. .day-head (globals.css) sets `top` to the top bar's
                height. The page color behind it (slightly see-through, blurred) keeps the
                rows scrolling underneath from showing through the text. -mx/px make the
                background reach the screen edges on phones. */}
            <div className="day-head sticky z-20 -mx-4 flex items-baseline gap-3 border-b border-line-strong bg-canvas/90 px-4 pt-3 pb-2.5 backdrop-blur-md md:mx-0 md:px-0">
              <h3 id={`day-${date}`} className="font-display text-2xl leading-none font-bold">
                {heading.main}
              </h3>
              <span className="text-sm text-muted">{heading.detail}</span>
              <span className="ml-auto text-sm text-muted tabular-nums">
                {dayGames.length} {dayGames.length === 1 ? "game" : "games"}
              </span>
            </div>
            <ul>
              {dayGames.map((game) => (
                <li
                  key={gameKey(game)}
                  // The hover band reaches past the column edges a little (-mx-3 px-3) so it
                  // frames the row instead of cutting the text off at the edges. The divider
                  // line can't be the li's own border then (it would stick out past the day
                  // heading's line), so it's drawn by ::after, pulled back in by the same
                  // 12px on each side (after:inset-x-3).
                  className="relative -mx-3 rounded-lg px-3 py-3.5 transition-colors after:absolute after:inset-x-3 after:bottom-0 after:h-px after:bg-line last:after:hidden hover:bg-panel"
                >
                  {renderGame(game)}
                </li>
              ))}
            </ul>
          </section>
        );
      })}

      {remaining > 0 && (
        <button
          type="button"
          onClick={() => setShownDays((n) => n + daysPerPage)}
          className="inline-flex h-10 items-center gap-2 rounded-full border border-line-strong bg-panel px-5 text-sm font-medium transition-colors hover:bg-raised"
        >
          {/* Says exactly what the button adds, and how much is left after that. */}
          Show {next} more {next === 1 ? "day" : "days"}
          <span className="font-normal text-muted tabular-nums">{remaining} left</span>
        </button>
      )}
    </div>
  );
}
