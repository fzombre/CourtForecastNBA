"use client";

// Controls: the form pieces the tabs share, built once here so every tab's filters look
// and behave the same.
//
//   Segmented   a row of joined buttons, one pressed, with a pill that glides between them
//               (e.g. All / East / West on Playoff odds)
//   TeamPicker  a searchable dropdown of teams with their logos (Upcoming & picks)
//   Toolbar     the row that holds a tab's filters, with a result count on the right

import { useId, useMemo, useRef, useState, type KeyboardEvent, type ReactNode } from "react";
import { useDismiss } from "@/lib/useDismiss";
import { useSlidingPill } from "@/lib/useSlidingPill";
import { CheckIcon, ChevronDownIcon, SearchIcon } from "./Icons";
import { TeamLogo } from "./Team";

// ---------------------------------------------------------------------------------------
// Segmented
// ---------------------------------------------------------------------------------------

type SegmentedProps<Value extends string> = {
  /** Read out to screen readers as the name of the group, e.g. "Conference". */
  label: string;
  value: Value;
  options: readonly Value[];
  onChange: (value: Value) => void;
};

/**
 * For choices with only a few options. Faster than a dropdown because every option is
 * visible and one click away. aria-pressed tells screen readers which one is on.
 */
export function Segmented<Value extends string>({ label, value, options, onChange }: SegmentedProps<Value>) {
  const rowRef = useRef<HTMLDivElement>(null);
  const pillRef = useRef<HTMLSpanElement>(null);
  useSlidingPill(rowRef, pillRef, '[aria-pressed="true"]', value);

  return (
    // max-w-full + overflow-x-auto: with many options on a phone, the row scrolls sideways.
    <div
      ref={rowRef}
      role="group"
      aria-label={label}
      className="relative inline-flex max-w-full overflow-x-auto rounded-full border border-line bg-panel p-1"
    >
      {/* The pill behind the pressed button. inset-y-1 matches the row's p-1 padding. */}
      <span
        ref={pillRef}
        aria-hidden
        className="sliding-pill absolute inset-y-1 left-0 rounded-full bg-raised shadow-[inset_0_0_0_1px_var(--line-strong)] transition-[transform,width] duration-300 ease-[cubic-bezier(0.2,0.7,0.2,1)]"
      />
      {options.map((option) => {
        const on = option === value;
        return (
          <button
            key={option}
            type="button"
            aria-pressed={on}
            onClick={() => onChange(option)}
            // `relative` puts the text above the absolutely-positioned pill.
            className={`relative rounded-full px-3.5 py-1 text-sm whitespace-nowrap transition-colors ${
              on ? "font-medium text-fg" : "text-muted hover:text-fg"
            }`}
          >
            {option}
          </button>
        );
      })}
    </div>
  );
}

// ---------------------------------------------------------------------------------------
// TeamPicker
// ---------------------------------------------------------------------------------------

export type TeamOption = { code: string; name: string };

type TeamPickerProps = {
  /** The text in front of the button, e.g. "Team". */
  label: string;
  teams: TeamOption[];
  /** The picked team's code, or null for "All teams". */
  value: string | null;
  onChange: (code: string | null) => void;
};

/**
 * A button that opens a list of teams with a search box on top (an ARIA "combobox").
 *
 * Mouse: click the button, click a team. Keyboard: Enter/Space/↓ on the button opens it
 * with the search box focused; type to filter; ↑/↓ move through the list; Enter picks;
 * Escape closes. Screen readers hear which option is highlighted through
 * aria-activedescendant, while the typing focus stays in the search box.
 */
export function TeamPicker({ label, teams, value, onChange }: TeamPickerProps) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [active, setActive] = useState(0); // the highlighted row, as a position in `shown`

  const rootRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const listRef = useRef<HTMLUListElement>(null);
  const id = useId(); // a unique prefix, so two pickers on one page never share ids
  const listId = `${id}-list`;

  // null in the list stands for "All teams", always first.
  const shown = useMemo<(TeamOption | null)[]>(() => {
    const q = query.trim().toLowerCase();
    const matches = teams.filter((t) => !q || t.name.toLowerCase().includes(q) || t.code.toLowerCase().includes(q));
    return q ? matches : [null, ...matches]; // while searching, hide "All teams"
  }, [teams, query]);

  const picked = teams.find((t) => t.code === value) ?? null;

  const close = (returnFocus: boolean) => {
    setOpen(false);
    setQuery("");
    if (returnFocus) buttonRef.current?.focus(); // so the keyboard user isn't lost
  };
  useDismiss(rootRef, open, () => close(true));

  const openList = () => {
    setOpen(true);
    // Start with the current pick highlighted (position +1 because "All teams" is first).
    setActive(value ? teams.findIndex((t) => t.code === value) + 1 : 0);
  };

  const choose = (team: TeamOption | null) => {
    onChange(team?.code ?? null);
    close(true);
  };

  /** Highlight row `index` and scroll it into view inside the list. */
  const highlight = (index: number) => {
    const next = Math.max(0, Math.min(shown.length - 1, index));
    setActive(next);
    listRef.current?.children[next]?.scrollIntoView({ block: "nearest" });
  };

  const onInputKey = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "ArrowDown") highlight(active + 1);
    else if (event.key === "ArrowUp") highlight(active - 1);
    else if (event.key === "Enter" && shown[active] !== undefined) choose(shown[active]);
    else if (event.key === "Tab") close(false); // tabbing away just closes
    else return;
    event.preventDefault(); // stop the arrows moving the cursor in the text box
  };

  const optionId = (index: number) => `${id}-opt-${index}`;

  return (
    <div className="inline-flex items-center gap-2 text-sm text-muted">
      <span id={`${id}-label`}>{label}</span>
      {/* The button and its popover share this `relative` box, so the popover opens right
          under the button. Both are inside rootRef, so useDismiss treats them as one. */}
      {/* While open, z-30 lifts the whole picker above the sticky day headings (z-20) of
          the list below it, which would otherwise slide over the popover's bottom edge. */}
      <div ref={rootRef} className={`relative ${open ? "z-30" : ""}`}>
      <button
        ref={buttonRef}
        type="button"
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-labelledby={`${id}-label ${id}-value`}
        onClick={() => (open ? close(false) : openList())}
        onKeyDown={(event) => {
          if (event.key === "ArrowDown" && !open) {
            event.preventDefault();
            openList();
          }
        }}
        className="inline-flex h-9 min-w-52 items-center gap-2 rounded-lg border border-line-strong bg-panel px-3 text-[15px] text-fg transition-colors hover:bg-raised"
      >
        {picked && <TeamLogo code={picked.code} size={18} />}
        <span id={`${id}-value`} className="truncate">
          {picked?.name ?? "All teams"}
        </span>
        <ChevronDownIcon className={`ml-auto text-muted transition-transform ${open ? "rotate-180" : ""}`} />
      </button>

      {open && (
        // The popover: one step lighter than the page, with a real shadow, because it
        // really does sit above everything else.
        // The width never exceeds the screen minus the 16px gutters on a phone.
        <div className="absolute top-full left-0 z-40 mt-2 w-[min(20rem,calc(100vw-2rem))] overflow-hidden rounded-xl border border-line-strong bg-raised shadow-[0_16px_40px_-12px_rgb(0_0_0/0.7)]">
          <div className="flex items-center gap-2 border-b border-line px-3">
            <SearchIcon className="text-muted" />
            <input
              autoFocus
              role="combobox"
              aria-expanded
              aria-controls={listId}
              aria-autocomplete="list"
              aria-activedescendant={shown.length ? optionId(active) : undefined}
              aria-label="Search teams"
              placeholder="Search teams"
              value={query}
              onChange={(event) => {
                setQuery(event.target.value);
                setActive(0); // a new search starts at the top of the results
              }}
              onKeyDown={onInputKey}
              className="h-11 w-full bg-transparent text-[15px] text-fg placeholder:text-muted focus:outline-none"
            />
          </div>

          <ul ref={listRef} id={listId} role="listbox" aria-label="Teams" className="max-h-72 overflow-y-auto p-1">
            {shown.map((team, index) => {
              const isPicked = (team?.code ?? null) === value;
              return (
                <li
                  key={team?.code ?? "all"}
                  id={optionId(index)}
                  role="option"
                  aria-selected={isPicked}
                  // onMouseDown + preventDefault keeps focus in the search box while clicking.
                  onMouseDown={(event) => event.preventDefault()}
                  onClick={() => choose(team)}
                  onMouseMove={() => active !== index && setActive(index)}
                  className={`flex cursor-pointer items-center gap-2.5 rounded-lg px-2.5 py-2 text-[15px] ${
                    index === active ? "bg-line-strong/60 text-fg" : "text-fg/90"
                  }`}
                >
                  {team ? (
                    <TeamLogo code={team.code} size={20} />
                  ) : (
                    <span aria-hidden className="inline-block size-5" />
                  )}
                  <span className="truncate">{team?.name ?? "All teams"}</span>
                  {isPicked && <CheckIcon className="ml-auto shrink-0 text-pick" />}
                </li>
              );
            })}
            {shown.length === 0 && <li className="px-2.5 py-3 text-sm text-muted">No team matches “{query}”.</li>}
          </ul>
        </div>
      )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------------------
// Toolbar
// ---------------------------------------------------------------------------------------

/** A row that holds a tab's filters, with the result count pushed to the right. */
export function Toolbar({ children, count }: { children: ReactNode; count?: string }) {
  return (
    <div className="mb-6 flex flex-wrap items-center gap-x-6 gap-y-3">
      {children}
      {count && <p className="text-sm text-muted tabular-nums sm:ml-auto">{count}</p>}
    </div>
  );
}
