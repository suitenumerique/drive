import { useCallback, useEffect, useState } from "react";

export type ViewMode = "list" | "grid";

export const LOCAL_STORAGE_KEY_VIEW_MODE = "explorerViewMode";

/**
 * The storage can be unavailable (private browsing, blocked site data), in
 * which case we fall back to the list view and do not persist the choice.
 */
export const getStoredViewMode = (): ViewMode => {
  try {
    return localStorage.getItem(LOCAL_STORAGE_KEY_VIEW_MODE) === "grid"
      ? "grid"
      : "list";
  } catch {
    return "list";
  }
};

export const storeViewMode = (viewMode: ViewMode) => {
  try {
    localStorage.setItem(LOCAL_STORAGE_KEY_VIEW_MODE, viewMode);
  } catch {
    // The choice simply won't survive a reload.
  }
};

export const useViewMode = () => {
  // Read after hydration: the prerendered page has no storage.
  const [viewMode, setViewMode] = useState<ViewMode>("list");

  useEffect(() => {
    setViewMode(getStoredViewMode());
  }, []);

  const changeViewMode = useCallback((value: ViewMode) => {
    setViewMode(value);
    storeViewMode(value);
  }, []);

  return { viewMode, setViewMode: changeViewMode };
};
