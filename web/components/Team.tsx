"use client";

// Team: a team's logo with its name to the right, used everywhere a team appears.
//
// The logos come straight from NBA.com's own image server (cdn.nba.com), the same files
// NBA.com uses. Each logo's address contains the team's NBA id, e.g.
//   https://cdn.nba.com/logos/nba/1610612738/primary/L/logo.svg   (Boston Celtics)
// The Python API sends the code -> id list in /api/overview ("team_ids"), and
// SettingsProvider turns a code into an id with teamId().
//
// "L" is the logo for light backgrounds. Six teams also have a "D" version drawn for dark
// backgrounds (for the others, D is the same file), so we let the browser pick: the
// <picture> element below uses D when your system is in dark mode, otherwise L.

import { useState } from "react";
import { useSettings } from "./SettingsProvider";

const LOGO_BASE = "https://cdn.nba.com/logos/nba";

/** Just the logo. `size` is its width and height in pixels. */
export function TeamLogo({ code, size = 20 }: { code: string; size?: number }) {
  const { teamId } = useSettings();
  const id = teamId(code);
  // Set to true if the logo can't be downloaded (no internet, or NBA.com refuses the
  // request). We then show the empty box below instead of the browser's broken-image icon.
  const [failed, setFailed] = useState(false);

  // Until /api/overview has loaded we don't know the id yet, and if the logo failed to
  // load there's nothing to show. Either way, show an empty box of the same size, so the
  // names stay lined up.
  if (id === undefined || failed) {
    return <span className="inline-block shrink-0" style={{ width: size, height: size }} aria-hidden />;
  }

  return (
    <picture className="shrink-0">
      <source media="(prefers-color-scheme: dark)" srcSet={`${LOGO_BASE}/${id}/primary/D/logo.svg`} />
      {/*
        A plain <img> instead of Next.js's <Image>: these are small SVG files from another
        website, so <Image>'s resizing service has nothing to do, and <Image> can't do the
        light/dark switch above.
        - alt="": the team's name is written right next to the logo, so a screen reader
          should skip the picture instead of reading the name twice.
        - loading="lazy": the browser only downloads logos as they scroll into view,
          which matters on tabs with a thousand rows.
      */}
      <img
        src={`${LOGO_BASE}/${id}/primary/L/logo.svg`}
        alt=""
        width={size}
        height={size}
        loading="lazy"
        decoding="async"
        onError={() => setFailed(true)}
        style={{ width: size, height: size }}
      />
    </picture>
  );
}

type TeamProps = {
  /** Three-letter team code, e.g. "BOS". */
  code: string;
  /** The name to show. Leave it out to use the full name from /api/overview. */
  name?: string;
  /** Logo size in pixels (20 fits a table row). */
  logoSize?: number;
};

/** The logo on the left, the team's name on the right. */
export default function Team({ code, name, logoSize = 20 }: TeamProps) {
  const { teamName } = useSettings();
  return (
    <span className="inline-flex items-center gap-2 align-middle">
      <TeamLogo code={code} size={logoSize} />
      <span>{name ?? teamName(code)}</span>
    </span>
  );
}
