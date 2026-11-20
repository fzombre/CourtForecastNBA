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
// backgrounds (for the others, D is the same file). The site only has a dark theme, so
// we always use D: otherwise teams with dark logos (e.g. the Nets) would vanish into the page.

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
    /*
      A plain <img> instead of Next.js's <Image>: these are small SVG files from another
      website, so <Image>'s resizing service has nothing to do.
      - alt="": the team's name is written right next to the logo, so a screen reader
        should skip the picture instead of reading the name twice.
      - loading="lazy": the browser only downloads logos as they scroll into view,
        which matters on tabs with a thousand rows.
    */
    // eslint-disable-next-line @next/next/no-img-element -- deliberate, see the comment above
    <img
      src={`${LOGO_BASE}/${id}/primary/D/logo.svg`}
      alt=""
      width={size}
      height={size}
      loading="lazy"
      decoding="async"
      onError={() => setFailed(true)}
      className="shrink-0"
      style={{ width: size, height: size }}
    />
  );
}

type TeamProps = {
  /** Three-letter team code, e.g. "BOS". */
  code: string;
  /** The name to show. Leave it out to use the full name from /api/overview. */
  name?: string;
  /** Logo size in pixels (20 fits a table row). */
  logoSize?: number;
  /**
   * On narrow screens, show the three-letter code ("BOS") instead of the full name, so a
   * row with two teams still fits on a phone. From the `sm` breakpoint up the full name shows.
   */
  compact?: boolean;
  /**
   * Put the logo after the name instead of before it. Used for the away team in matchups
   * and scorelines, so both logos sit next to the middle of the row, facing each other.
   */
  logoAfter?: boolean;
};

/** The team's logo next to its name. */
export default function Team({ code, name, logoSize = 20, compact = false, logoAfter = false }: TeamProps) {
  const { teamName } = useSettings();
  const fullName = name ?? teamName(code);

  const label = compact ? (
    <>
      {/* Two spans, one hidden at each screen size. title= shows the full name when you
          hover the short code on a phone-sized window. */}
      <span className="sm:hidden" title={fullName}>
        {code}
      </span>
      <span className="hidden sm:inline">{fullName}</span>
    </>
  ) : (
    <span>{fullName}</span>
  );

  return (
    <span className={`inline-flex min-w-0 items-center gap-2 align-middle ${logoAfter ? "flex-row-reverse" : ""}`}>
      <TeamLogo code={code} size={logoSize} />
      {label}
    </span>
  );
}
