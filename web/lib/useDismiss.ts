"use client";

// useDismiss: closes a popover (the team picker, the data-status panel) when you click
// anywhere outside it or press Escape, the way every menu on a desktop behaves.

import { useEffect, useRef, type RefObject } from "react";

/**
 * While `open` is true, call `onClose` when:
 *   - the mouse or a finger presses down anywhere outside `ref` (the popover AND the
 *     button that opens it should both be inside `ref`, so clicking the button again
 *     toggles instead of closing and instantly reopening), or
 *   - the Escape key is pressed.
 */
export function useDismiss(ref: RefObject<HTMLElement | null>, open: boolean, onClose: () => void) {
  // Keep the latest onClose in a ref, so the listeners below don't have to be removed and
  // added again every time the parent re-renders with a new function.
  const onCloseRef = useRef(onClose);
  useEffect(() => {
    onCloseRef.current = onClose;
  });

  useEffect(() => {
    if (!open) return;

    const onPointerDown = (event: PointerEvent) => {
      if (ref.current && !ref.current.contains(event.target as Node)) onCloseRef.current();
    };
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onCloseRef.current();
    };

    document.addEventListener("pointerdown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("pointerdown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [ref, open]);
}
