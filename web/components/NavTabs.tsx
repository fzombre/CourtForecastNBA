"use client";

// NavTabs: the row of tabs inside the sticky top bar. Each tab is its own page (its own
// URL), so you can bookmark a tab or use the browser's back button, which the Streamlit
// tabs couldn't do.
//
// The tab you're on sits on a softly lit gold pill. When you click another tab, the pill
// glides over to it (useSlidingPill), so you see where you went.

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef } from "react";
import { useSlidingPill } from "@/lib/useSlidingPill";

/**
 * The tabs, in order. `href` is the page's URL. The first five and "Model" are the six
 * tabs of the Streamlit app; "MVP" exists only on this website (see src/mvp.py). It sits
 * after Playoff odds because both answer "who's going to win?"; Model stays last as the
 * "how does it work" page. The label is just "MVP" (the page's title says "MVP race")
 * so that seven tabs still fit in the desktop top bar.
 */
const TABS = [
  { href: "/", label: "Results" },
  { href: "/upcoming", label: "Upcoming & picks" },
  { href: "/standings", label: "Standings" },
  { href: "/predicted", label: "Predicted" },
  { href: "/odds", label: "Playoff odds" },
  { href: "/mvp", label: "MVP" },
  { href: "/model", label: "Model" },
];

export default function NavTabs() {
  // The current URL path, e.g. "/odds". Used to highlight the tab you're on.
  const pathname = usePathname();

  const rowRef = useRef<HTMLUListElement>(null);
  const pillRef = useRef<HTMLSpanElement>(null);
  useSlidingPill(rowRef, pillRef, '[aria-current="page"]', pathname);

  // On phones the tab row scrolls sideways, so a tab near the end ("Model") can be
  // off-screen. After each page change, scroll the row (only the row, not the page:
  // block "nearest") just far enough that the current tab is visible.
  const activeRef = useRef<HTMLAnchorElement>(null);
  useEffect(() => {
    activeRef.current?.scrollIntoView({ block: "nearest", inline: "nearest" });
  }, [pathname]);

  return (
    // On small screens the row bleeds to the screen edges (-mx-4 px-4) and scrolls
    // sideways (overflow-x-auto) instead of wrapping into a messy second line.
    <nav aria-label="Sections" className="-mx-4 h-full overflow-x-auto px-4 md:-mx-8 md:px-8 lg:mx-0 lg:px-0">
      <ul ref={rowRef} className="relative flex h-full min-w-max items-center gap-1">
        {/* The pill: 32px tall, centered vertically (top = 50% - 16px; a translateY would
            clash with the translateX that useSlidingPill writes into `transform`). */}
        <span
          ref={pillRef}
          aria-hidden
          className="sliding-pill absolute top-[calc(50%-16px)] left-0 h-8 rounded-full bg-pick/12 shadow-[inset_0_0_0_1px_color-mix(in_oklab,var(--pick)_30%,transparent)] transition-[transform,width] duration-300 ease-[cubic-bezier(0.2,0.7,0.2,1)]"
        />
        {TABS.map((tab) => {
          const active = pathname === tab.href;
          return (
            <li key={tab.href}>
              {/* <Link> switches pages without reloading the whole site, so the header and
                  the data it already loaded stay as they are. aria-current tells screen
                  readers (and useSlidingPill) which tab is the current page. */}
              <Link
                ref={active ? activeRef : undefined}
                href={tab.href}
                aria-current={active ? "page" : undefined}
                // lg:px-3: on desktops all seven tabs share one row with the wordmark and
                // the buttons, so each tab gives up 2px a side to fit them without scrolling.
                className={`relative flex h-8 items-center rounded-full px-3.5 text-sm whitespace-nowrap transition-colors lg:px-3 ${
                  active ? "font-medium text-pick" : "text-muted hover:text-fg"
                }`}
              >
                {tab.label}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
