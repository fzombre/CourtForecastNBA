// Controls: the form pieces the tabs share (a dropdown and a row of toggle buttons),
// styled once here so every tab's filters look and behave the same.

import type { ReactNode } from "react";

type SelectProps = {
  /** The text in front of the dropdown, e.g. "Team". Clicking it focuses the dropdown. */
  label: string;
  value: string;
  options: string[];
  onChange: (value: string) => void;
};

/** A labeled dropdown. The native <select> is kept (good on phones and with keyboards),
 *  only its border, padding and colors are restyled. */
export function Select({ label, value, options, onChange }: SelectProps) {
  return (
    <label className="inline-flex items-center gap-2 text-sm text-ink-muted">
      {label}
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="rounded-md border border-rule bg-floor-alt px-2.5 py-1.5 text-[15px] text-ink hover:border-ink-muted"
      >
        {options.map((option) => (
          <option key={option}>{option}</option>
        ))}
      </select>
    </label>
  );
}

type SegmentedProps<Value extends string> = {
  /** Read out to screen readers as the name of the group, e.g. "Conference". */
  label: string;
  value: Value;
  options: readonly Value[];
  onChange: (value: Value) => void;
};

/**
 * A row of joined buttons where exactly one is pressed, for choices with only a few options
 * (e.g. All / East / West). Faster than a dropdown because every option is visible.
 * aria-pressed tells screen readers which one is on.
 */
export function Segmented<Value extends string>({ label, value, options, onChange }: SegmentedProps<Value>) {
  return (
    <div role="group" aria-label={label} className="inline-flex rounded-full border border-rule bg-floor-alt p-0.5">
      {options.map((option) => {
        const on = option === value;
        return (
          <button
            key={option}
            type="button"
            aria-pressed={on}
            onClick={() => onChange(option)}
            className={`rounded-full px-3.5 py-1 text-sm transition-colors ${
              on ? "bg-ink font-medium text-floor" : "text-ink-muted hover:text-ink"
            }`}
          >
            {option}
          </button>
        );
      })}
    </div>
  );
}

/** A row that holds a tab's filters, with the result count pushed to the right. */
export function Toolbar({ children, count }: { children: ReactNode; count?: string }) {
  return (
    <div className="mb-6 flex flex-wrap items-center gap-x-6 gap-y-3">
      {children}
      {count && <p className="text-sm text-ink-muted sm:ml-auto">{count}</p>}
    </div>
  );
}
