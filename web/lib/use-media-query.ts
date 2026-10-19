"use client";

import { useEffect, useState } from "react";

/**
 * SSR-safe media query.
 *
 * Always returns `false` on the server and on the first client render, then
 * settles after mount. Reading `window.matchMedia` during render would produce
 * different markup on server and client and trip React's hydration check.
 */
export function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState(false);

  useEffect(() => {
    const list = window.matchMedia(query);
    const sync = () => setMatches(list.matches);
    sync();

    // `change` is the right event, but it does not fire in every environment
    // (devtools viewport emulation, some embedded webviews). Re-reading
    // `list.matches` on resize costs nothing and stops the layout getting
    // stuck in the wrong mode.
    list.addEventListener("change", sync);
    window.addEventListener("resize", sync);
    return () => {
      list.removeEventListener("change", sync);
      window.removeEventListener("resize", sync);
    };
  }, [query]);

  return matches;
}

/** Matches Tailwind's `lg` breakpoint, where the rails stop being overlays. */
export const useIsDesktop = () => useMediaQuery("(min-width: 1024px)");
