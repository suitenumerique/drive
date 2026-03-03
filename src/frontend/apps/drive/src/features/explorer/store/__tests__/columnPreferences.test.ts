import {
  ColumnType,
  DEFAULT_COLUMN_PREFERENCES,
} from "../../types/columns";
import { LocalStorageColumnPreferencesStore } from "../columnPreferences";

const STORAGE_KEY = "drive:column-preferences";

// Mock localStorage for node test environment
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: (key: string) => store[key] ?? null,
    setItem: (key: string, value: string) => {
      store[key] = value;
    },
    clear: () => {
      store = {};
    },
    removeItem: (key: string) => {
      delete store[key];
    },
  };
})();
Object.defineProperty(global, "localStorage", { value: localStorageMock });
Object.defineProperty(global, "window", { value: global, writable: true });

describe("LocalStorageColumnPreferencesStore", () => {
  let store: LocalStorageColumnPreferencesStore;

  beforeEach(() => {
    localStorage.clear();
    store = new LocalStorageColumnPreferencesStore();
  });

  it("returns defaults when localStorage is empty", () => {
    expect(store.get()).toEqual(DEFAULT_COLUMN_PREFERENCES);
  });

  it("returns defaults on corrupted JSON", () => {
    localStorage.setItem(STORAGE_KEY, "not-valid-json{{{");
    expect(store.get()).toEqual(DEFAULT_COLUMN_PREFERENCES);
  });

  it("persists and retrieves preferences", () => {
    const prefs = {
      column1: ColumnType.FILE_SIZE,
      column2: ColumnType.FILE_TYPE,
    };
    store.set(prefs);
    expect(store.get()).toEqual(prefs);
  });

  it("persists across store instances", () => {
    const prefs = {
      column1: ColumnType.CREATED,
      column2: ColumnType.CREATED_BY,
    };
    store.set(prefs);

    const store2 = new LocalStorageColumnPreferencesStore();
    expect(store2.get()).toEqual(prefs);
  });
});
