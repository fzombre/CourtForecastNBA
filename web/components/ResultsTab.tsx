"use client";

// Tab 1 (Results): every finished game, newest day first, with a filter for the type of game.
//
// Each game is a scoreline, laid out like a scoreboard (see .scoreline in globals.css):
//
//      Boston Celtics [logo]  112  –  108  [logo] Denver Nuggets
//
// The winner's name and score are set bold in ink and the loser's in the muted color, so
// the winner is clear without a separate "Winner" column.

import { useState } from "react";
import { useApi } from "./SettingsProvider";
import { Info, LoadingOrError } from "./Table";
import { Select, Toolbar } from "./Controls";
import GameDays from "./GameDays";
import Team from "./Team";
import type { PlayedGame } from "@/lib/types";

/** Classes for one side of the score: bold ink for the winner, muted for the loser. A tie
 *  (only in odd preseason games, winner = null) leaves both sides plain ink. */
function sideClass(game: PlayedGame, code: string): string {
  if (game.winner === null) return "text-ink";
  return game.winner === code ? "font-semibold text-ink" : "text-ink-muted";
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
      <span aria-hidden className="text-center text-ink-muted">
        –
      </span>
      <span className={`text-lg tabular-nums ${home}`}>{game.home_score}</span>
      <span className={`flex ${home}`}>
        <Team code={game.home} name={game.home_name} compact />
      </span>
      {/* Only non-regular-season games get a label; on phones it would crowd the row, so
          it shows from the md breakpoint up (the filter above still covers phones). */}
      <span className="hidden text-right text-sm text-ink-muted md:block">
        {game.stage !== "Regular Season" ? game.stage : ""}
      </span>
    </div>
  );
}

export default function ResultsTab() {
  // Results don't depend on the number of simulations, so the path never changes.
  const { data: games, error } = useApi<PlayedGame[]>("/api/results");
  const [stage, setStage] = useState("All"); // the "Show" dropdown

  if (!games) return <LoadingOrError error={error} what="results" />;

  // The dropdown lists "All" plus every type of game that has been played, A to Z.
  // new Set(...) removes duplicates; [...set] turns it back into a list.
  const stages = ["All", ...[...new Set(games.map((g) => g.stage))].sort()];
  const shown = stage === "All" ? games : games.filter((g) => g.stage === stage);

  return (
    <section>
      <Toolbar count={`${shown.length} ${shown.length === 1 ? "game" : "games"}`}>
        <Select label="Show" value={stage} options={stages} onChange={setStage} />
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
