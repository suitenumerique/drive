import {
  ColumnPreferences,
  DEFAULT_COLUMN_PREFERENCES,
} from "../types/columns";

export interface ColumnPreferencesStore {
  get(): ColumnPreferences;
  set(prefs: ColumnPreferences): void;
}

const STORAGE_KEY = "drive:column-preferences";

export class LocalStorageColumnPreferencesStore
  implements ColumnPreferencesStore
{
  get(): ColumnPreferences {
    if (typeof window === "undefined") return DEFAULT_COLUMN_PREFERENCES;
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return DEFAULT_COLUMN_PREFERENCES;
    try {
      return JSON.parse(raw) as ColumnPreferences;
    } catch {
      return DEFAULT_COLUMN_PREFERENCES;
    }
  }

  set(prefs: ColumnPreferences): void {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs));
  }
}
