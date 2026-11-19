"use client";

// NavTabs: the row of tabs. Each tab is its own page (its own URL), so you can bookmark
// a tab or use the browser's back button, which the Streamlit tabs couldn't do.
//
// The look borrows from the court: the whole row sits on a thin line, and the tab you're
// on gets a thick painted stripe in the accent color, like the edge of the key.

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef } from "react";

/** The six tabs of the Streamlit app, in the same order. `href` is the page's URL. */
const TABS = [
  { href: "/", label: "Results" },
  { href: "/upcoming", label: "Upcoming & picks" },
  { href: "/standings", label: "Standings" },
  { href: "/predicted", label: "Predicted standings" },
  { href: "/odds", label: "Playoff odds" },
  { href: "/model", label: "Model" },
];

export default function NavTabs() {
  // The current URL path, e.g. "/odds". Used to highlight the tab you're on.
  const pathname = usePathname();

  // On phones the tab row scrolls sideways, so a tab near the end ("Model") can be
  // off-screen. After each page change, scroll the row (only the row, not the page:
  // block "nearest") just far enough that the current tab is visible.
  const activeRef = useRef<HTMLAnchorElement>(null);
  useEffect(() => {
    activeRef.current?.scrollIntoView({ block: "nearest", inline: "nearest" });
  }, [pathname]);

  return (
    // On phones the six tabs don't fit on one line, so the row scrolls sideways
    // (overflow-x-auto) instead of wrapping into a messy second row.
    <nav aria-label="Sections" className="mt-8 -mx-4 overflow-x-auto px-4 md:mx-0 md:px-0">
      <ul className="flex min-w-max gap-6 border-b border-rule">
        {TABS.map((tab) => {
          const active = pathname === tab.href;
          return (
            <li key={tab.href}>
              {/* <Link> switches pages without reloading the whole site, so the header and
                  the data it already loaded stay as they are. aria-current tells screen
                  readers which tab is the current page. */}
              <Link
                ref={active ? activeRef : undefined}
                href={tab.href}
                aria-current={active ? "page" : undefined}
                className={`-mb-px block border-b-[3px] pb-2.5 text-[15px] whitespace-nowrap transition-colors ${
                  active
                    ? "border-paint font-semibold text-ink"
                    : "border-transparent text-ink-muted hover:border-rule hover:text-ink"
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
