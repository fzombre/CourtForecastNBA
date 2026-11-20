"use client";

// Tab 1 (Results): every finished game, newest day first, with a filter for the type of game.
//
// Each game is a scoreline, laid out like a scoreboard (see .scoreline in globals.css):
//
//      Boston Celtics [logo]  112  –  108  [logo] Denver Nuggets
//
// The winner's name and score are set bold in the main text color and the loser's in the
// muted color, so the winner is clear without a separate "Winner" column.

import { useState } from "react";
import { useApi } from "./SettingsProvider";
import { Info, LoadingOrError } from "./Table";
import { Segmented, Toolbar } from "./Controls";
import GameDays from "./GameDays";
import Team from "./Team";
import type { PlayedGame, Stage } from "@/lib/types";

/** Every type of game, in the order they happen in a season (see STAGES in src/data.py). */
const STAGE_ORDER: Stage[] = ["Preseason", "Regular Season", "NBA Cup Final", "Play-In", "Playoffs", "Other"];

/** Classes for one side of the score: bold for the winner, muted for the loser. A tie
 *  (only in odd preseason games, winner = null) leaves both sides plain. */
function sideClass(game: PlayedGame, code: string): string {
  if (game.winner === null) return "text-fg";
  return game.winner === code ? "font-semibold text-fg" : "text-muted";
}

function Scoreline({ game }: { game: PlayedGame }) {
  const away = sideClass(game, game.away);
  const home = sideClass(game, game.home);
  return (
    <div className="scoreline">
      <span className={`flex justify-end text-right ${away}`}>
        <Team code={game.away} name={game.away_name} compact logoAfter />
      </span>
      <span className={`text-right text-lg tabular-nums ${away}`}>{game.away_score}</span>
      <span aria-hidden className="text-center text-muted/60">
        –
      </span>
      <span className={`text-lg tabular-nums ${home}`}>{game.home_score}</span>
      <span className={`flex ${home}`}>
        <Team code={game.home} name={game.home_name} compact />
      </span>
      {/* Only non-regular-season games get a label, as a small badge; on phones it would
          crowd the row, so it shows from the md breakpoint up (the filter covers phones). */}
      <span className="hidden justify-end md:flex">
        {game.stage !== "Regular Season" && (
          <span className="rounded-full border border-line-strong px-2.5 py-0.5 text-[13px] text-muted">
            {game.stage}
          </span>
        )}
      </span>
    </div>
  );
}

export default function ResultsTab() {
  // Results don't depend on the number of simulations, so the path never changes.
  const { data: games, error } = useApi<PlayedGame[]>("/api/results");
  const [stage, setStage] = useState("All"); // the game-type filter

  if (!games) return <LoadingOrError error={error} what="results" />;

  // The filter lists "All" plus every type of game that has been played, in a fixed
  // order (season order, not A to Z): Preseason, Regular Season, NBA Cup Final, ...
  const played = new Set(games.map((g) => g.stage));
  const stages = ["All", ...STAGE_ORDER.filter((s) => played.has(s))];
  const shown = stage === "All" ? games : games.filter((g) => g.stage === stage);

  return (
    <section>
      <Toolbar count={`${shown.length} ${shown.length === 1 ? "game" : "games"}`}>
        <Segmented label="Type of game" value={stage} options={stages} onChange={setStage} />
      </Toolbar>
      {/* key={stage}: changing the filter starts the list over from the newest days. */}
      <GameDays
        key={stage}
        games={shown}
        gameKey={(g) => g.game_id}
        renderGame={(g) => <Scoreline game={g} />}
        empty={<Info>No finished games yet. Results show up here once games are played.</Info>}
      />
    </section>
  );
}
