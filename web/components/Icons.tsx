// Icons: the few small line icons the interface uses, drawn as inline SVG.
//
// Inline SVG (instead of an icon library) keeps the site free of extra dependencies, and
// `currentColor` makes each icon take the text color of whatever it sits in. They're all
// decorative (aria-hidden): every icon sits next to text, or inside a button that has an
// aria-label, so screen readers never need to describe the picture itself.

import type { SVGProps } from "react";

type IconProps = SVGProps<SVGSVGElement> & { size?: number };

/** Shared frame for every icon: a 24×24 drawing, 1.75px rounded strokes, no fill. */
function Icon({ size = 16, children, ...rest }: IconProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.75}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
      {...rest}
    >
      {children}
    </svg>
  );
}

/** Two arrows chasing each other in a circle: "load the data again". */
export function RefreshIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="M20 11a8 8 0 0 0-14.7-4.3L4 8" />
      <path d="M4 3v5h5" />
      <path d="M4 13a8 8 0 0 0 14.7 4.3L20 16" />
      <path d="M20 21v-5h-5" />
    </Icon>
  );
}

/** A "v": something opens below. */
export function ChevronDownIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="m6 9 6 6 6-6" />
    </Icon>
  );
}

/** "<": go back one step. */
export function ChevronLeftIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="m15 6-6 6 6 6" />
    </Icon>
  );
}

/** ">": go forward one step. */
export function ChevronRightIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="m9 6 6 6-6 6" />
    </Icon>
  );
}

/** A magnifying glass, at the start of a search box. */
export function SearchIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <circle cx="11" cy="11" r="7" />
      <path d="m20 20-3.5-3.5" />
    </Icon>
  );
}

/** A check mark, next to the option that's currently picked. */
export function CheckIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="m5 12.5 4.5 4.5L19 7.5" />
    </Icon>
  );
}
