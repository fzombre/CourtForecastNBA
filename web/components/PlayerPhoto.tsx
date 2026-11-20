"use client";

// PlayerPhoto: a player's headshot in a circle, used on the MVP race tab.
//
// Like the team logos (Team.tsx), the photos come straight from NBA.com's own image
// server. Each address contains the player's NBA id, which /api/mvp sends as player_id:
//   https://cdn.nba.com/headshots/nba/latest/260x190/1628983.png   (Shai Gilgeous-Alexander)
// "260x190" is the size of the file NBA.com serves: big enough to look sharp in our
// largest (96px) circle on a high-density phone screen, small enough to load quickly.
//
// The photo is a wide rectangle with the head near the top, so inside the circle it's
// scaled to fill (object-cover) and pinned to the top (object-top), which keeps the face
// in the middle of the circle instead of the shoulders.

import { useState } from "react";

const HEADSHOT_BASE = "https://cdn.nba.com/headshots/nba/latest/260x190";

/** "Nikola Jokić" -> "NJ"; "Shai Gilgeous-Alexander" -> "SG". Shown when there's no photo. */
function initials(name: string): string {
  const words = name.split(/\s+/).filter(Boolean);
  const first = words[0]?.[0] ?? "";
  const last = words.length > 1 ? words[words.length - 1][0] : "";
  return (first + last).toUpperCase();
}

type PlayerPhotoProps = {
  playerId: number;
  /** Used for the initials if the photo can't load. The name is always written next to
   *  the photo, so the picture itself is decorative (alt=""). */
  name: string;
  /** Width and height of the circle in pixels. */
  size?: number;
};

export default function PlayerPhoto({ playerId, name, size = 32 }: PlayerPhotoProps) {
  // Set to true if the photo can't be downloaded (no internet, a brand-new player who
  // has no NBA.com photo yet). We then show his initials instead of a broken image.
  const [failed, setFailed] = useState(false);

  return (
    // The circle: a raised surface with a faint ring, so photos with a transparent or
    // light background still read as a round shape on the dark page.
    <span
      aria-hidden
      className="relative inline-flex shrink-0 items-center justify-center overflow-hidden rounded-full bg-raised ring-1 ring-line-strong"
      style={{ width: size, height: size }}
    >
      {failed ? (
        <span className="font-display font-bold text-muted" style={{ fontSize: size * 0.38 }}>
          {initials(name)}
        </span>
      ) : (
        // A plain <img>, for the same reasons as TeamLogo: a small file from another
        // website, so Next.js's <Image> resizing service has nothing to add.
        // eslint-disable-next-line @next/next/no-img-element -- deliberate, see the comment above
        <img
          src={`${HEADSHOT_BASE}/${playerId}.png`}
          alt=""
          loading="lazy"
          decoding="async"
          onError={() => setFailed(true)}
          className="size-full object-cover object-top"
        />
      )}
    </span>
  );
}
