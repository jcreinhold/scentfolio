import { useCallback, useState } from "react";

export type ViewMode = "cards" | "table";

const STORAGE_KEY = "scentfolio:view";
const DEFAULT: ViewMode = "cards";

function isViewMode(v: unknown): v is ViewMode {
  return v === "cards" || v === "table";
}

/** Read the persisted view once, tolerating unavailable/blocked storage. */
function readStored(): ViewMode {
  try {
    const raw = typeof window !== "undefined" ? window.localStorage.getItem(STORAGE_KEY) : null;
    return isViewMode(raw) ? raw : DEFAULT;
  } catch {
    return DEFAULT;
  }
}

/**
 * Collection view preference, persisted across reloads.
 * The localStorage plumbing (availability guard, validation, write-through) is
 * hidden here so callers just use it like any other useState pair.
 */
export function useViewMode(): [ViewMode, (mode: ViewMode) => void] {
  const [view, setViewState] = useState<ViewMode>(readStored);

  const setView = useCallback((mode: ViewMode) => {
    setViewState(mode);
    try {
      window.localStorage.setItem(STORAGE_KEY, mode);
    } catch {
      /* non-fatal: keep the in-memory value */
    }
  }, []);

  return [view, setView];
}
