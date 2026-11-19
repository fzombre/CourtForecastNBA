"use client";

// NavTabs: the row of tabs. Each tab is its own page (its own URL), so you can bookmark
// a tab or use the browser's back button, which the Streamlit tabs couldn't do.

import Link from "next/link";
import { usePathname } from "next/navigation";

/** The six tabs of the Streamlit app, in the same order. `href` is the page's URL. */
const TABS = [
  { href: "/", label: "✅ Results" },
  { href: "/upcoming", label: "📅 Upcoming & picks" },
  { href: "/standings", label: "📊 Standings" },
  { href: "/predicted", label: "🔮 Predicted standings" },
  { href: "/odds", label: "🏆 Playoff odds" },
  { href: "/model", label: "🧠 Model" },
];

export default function NavTabs() {
  // The current URL path, e.g. "/odds". Used to highlight the tab you're on.
  const pathname = usePathname();

  return (
    <nav className="mb-6 flex flex-wrap gap-1 border-b border-zinc-200 dark:border-zinc-800">
      {TABS.map((tab) => {
        const active = pathname === tab.href;
        return (
          // <Link> switches pages without reloading the whole site, so the header and
          // the data it already loaded stay as they are.
          <Link
            key={tab.href}
            href={tab.href}
            className={`-mb-px border-b-2 px-3 py-2 text-sm ${
              active
                ? "border-orange-500 font-semibold"
                : "border-transparent text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-100"
            }`}
          >
            {tab.label}
          </Link>
        );
      })}
    </nav>
  );
}
