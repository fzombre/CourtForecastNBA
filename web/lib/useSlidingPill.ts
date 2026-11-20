"use client";

// useSlidingPill: moves a highlight "pill" behind whichever item in a row is selected, and
// lets it glide from the old item to the new one when the selection changes.
//
// Used by the tab bar (NavTabs.tsx) and the segmented filters (Controls.tsx). The motion
// answers your click: you see the highlight travel to what you picked.
//
// How it works:
//   - `rowRef` is the row (positioned `relative`); `pillRef` is an empty element inside it
//     (positioned `absolute`), drawn behind the items.
//   - The selected item is found with `selector` (e.g. '[aria-current="page"]').
//   - We read that item's position and size (offsetLeft/offsetWidth, relative to the row)
//     and write them straight onto the pill's style.
//
// Writing to the DOM directly (instead of keeping the position in React state) means no
// extra re-render each time, and it's the pattern React recommends for measuring layout.
//
// The first time, the pill is placed without a transition, so it doesn't fly in from the
// left edge when the page loads; after that it glides.

import { useLayoutEffect, useRef, type RefObject } from "react";

export function useSlidingPill(
  rowRef: RefObject<HTMLElement | null>,
  pillRef: RefObject<HTMLElement | null>,
  selector: string,
  /** Changes whenever the selection does (e.g. the current URL or the picked option). */
  selected: unknown,
) {
  const placedOnce = useRef(false);

  // useLayoutEffect runs after React updates the page but before the browser paints, so
  // the pill is already in the right place in the very first frame you see.
  useLayoutEffect(() => {
    const row = rowRef.current;
    const pill = pillRef.current;
    if (!row || !pill) return;

    const place = () => {
      const item = row.querySelector<HTMLElement>(selector);
      if (!item) {
        pill.style.opacity = "0"; // nothing selected (e.g. a page that isn't a tab): hide it
        return;
      }
      pill.style.opacity = "1";
      pill.style.width = `${item.offsetWidth}px`;
      pill.style.transform = `translateX(${item.offsetLeft}px)`;
    };

    if (!placedOnce.current) {
      // First placement: no animation. Re-enable the transition on the next frame.
      pill.style.transition = "none";
      place();
      requestAnimationFrame(() => {
        pill.style.transition = "";
      });
      placedOnce.current = true;
    } else {
      place();
    }

    // Item sizes change when the web fonts finish loading or the window is resized, so
    // re-measure then too (without these the pill could end up a few pixels off).
    const observer = new ResizeObserver(place);
    observer.observe(row);
    document.fonts?.ready.then(place);
    return () => observer.disconnect();
  }, [rowRef, pillRef, selector, selected]);
}
