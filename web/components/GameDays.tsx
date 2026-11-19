"use client";

// GameDays: a long list of games split into days ("Today", "Tomorrow", "Friday, Nov 20"),
// showing a few days at a time with a button to load more.
//
// Used by Results (newest day first) and Upcoming (soonest day first). Both lists can hold
// close to a thousand games; drawing them all at once would make the page slow and endless
// to scroll, and almost nobody needs more than the next or last few days.
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

  return (
    <div className="space-y-10">
      {days.slice(0, shownDays).map(([date, dayGames]) => {
        const heading = dayHeading(date);
        return (
          // aria-labelledby names each day's section after its heading, so screen reader
          // users can jump between days.
          <section key={date} aria-labelledby={`day-${date}`}>
            <div className="mb-1 flex items-baseline gap-3 border-b-2 border-ink pb-2">
              <h3 id={`day-${date}`} className="font-display text-2xl leading-none font-bold">
                {heading.main}
              </h3>
              <span className="text-sm text-ink-muted">{heading.detail}</span>
              <span className="ml-auto text-sm text-ink-muted">
                {dayGames.length} {dayGames.length === 1 ? "game" : "games"}
              </span>
            </div>
            <ul>
              {dayGames.map((game) => (
                <li key={gameKey(game)} className="border-b border-rule py-3 transition-colors hover:bg-floor-alt">
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
          className="rounded-full border border-ink px-4 py-1.5 text-sm font-medium transition-colors hover:bg-ink hover:text-floor"
        >
          {/* Says exactly what the button adds, and how much is left after that. */}
          Show {Math.min(daysPerPage, remaining)} more {Math.min(daysPerPage, remaining) === 1 ? "day" : "days"}
          <span className="text-ink-muted"> ({remaining} left)</span>
        </button>
      )}
    </div>
  );
}
