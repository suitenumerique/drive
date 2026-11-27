import {
  getStoredViewMode,
  LOCAL_STORAGE_KEY_VIEW_MODE,
  storeViewMode,
} from "../useViewMode";

const stubLocalStorage = (storage: Partial<Storage>) => {
  Object.defineProperty(globalThis, "localStorage", {
    value: storage,
    configurable: true,
  });
};

describe("view mode storage", () => {
  afterEach(() => {
    delete (globalThis as { localStorage?: Storage }).localStorage;
  });

  it("restores the stored view mode", () => {
    const values = new Map<string, string>();
    stubLocalStorage({
      getItem: (key) => values.get(key) ?? null,
      setItem: (key, value) => values.set(key, value),
    });

    expect(getStoredViewMode()).toBe("list");
    storeViewMode("grid");
    expect(values.get(LOCAL_STORAGE_KEY_VIEW_MODE)).toBe("grid");
    expect(getStoredViewMode()).toBe("grid");
  });

  it("falls back to the list view on unknown values", () => {
    stubLocalStorage({ getItem: () => "tiles" });
    expect(getStoredViewMode()).toBe("list");
  });

  it("falls back to the list view when the storage is unavailable", () => {
    const throwing = () => {
      throw new Error("SecurityError");
    };
    stubLocalStorage({ getItem: throwing, setItem: throwing });

    expect(getStoredViewMode()).toBe("list");
    expect(() => storeViewMode("grid")).not.toThrow();
  });
});
