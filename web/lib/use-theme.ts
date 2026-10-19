"use client";

import { useCallback, useEffect, useState } from "react";

type Theme = "light" | "dark";
const KEY = "theme";

/**
 * Explicit light/dark override on top of the OS preference.
 *
 * Writes `data-theme` on <html>, which the stylesheet lets win over
 * `prefers-color-scheme` in both directions. Starts as `null` so the first
 * paint keeps whatever the inline boot script already applied.
 */
export function useTheme() {
  const [theme, setTheme] = useState<Theme | null>(null);

  useEffect(() => {
    const stored = localStorage.getItem(KEY);
    if (stored === "light" || stored === "dark") {
      // Re-apply the override on load; the stylesheet alone only knows the OS
      // preference, so without this a stored choice is lost on refresh.
      document.documentElement.dataset.theme = stored;
      setTheme(stored);
      return;
    }
    setTheme(
      window.matchMedia("(prefers-color-scheme: dark)").matches
        ? "dark"
        : "light",
    );
  }, []);

  const toggle = useCallback(() => {
    setTheme((current) => {
      const next: Theme = current === "dark" ? "light" : "dark";
      document.documentElement.dataset.theme = next;
      localStorage.setItem(KEY, next);
      return next;
    });
  }, []);

  return { theme, toggle };
}
