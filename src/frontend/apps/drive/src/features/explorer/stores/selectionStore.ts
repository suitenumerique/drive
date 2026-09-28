import {
  createContext,
  useCallback,
  useContext,
  useRef,
  useSyncExternalStore,
} from "react";
import { Item } from "@/features/drivers/types";

type Listener = () => void;

export type SetSelectedItemsAction =
  | Item[]
  | ((prev: Item[]) => Item[]);

/**
 * External store for explorer selection state.
 *
 * The goal is to decouple selection updates from the render of the grid and
 * its cells: during a marquee drag, `setSelectedItems` is called on every
 * mousemove, and React's context propagation was forcing every row + cell
 * (200+) to re-render. With this store, each row subscribes via
 * `useIsItemSelected(id)` scoped to its own id — React bails out when the
 * snapshot value is unchanged, so only the rows whose selected status
 * actually flipped re-render.
 */
export class SelectionStore {
  private items: Item[] = [];
  private itemsById: Map<string, Item> = new Map();
  private readonly globalListeners: Set<Listener> = new Set();
  private readonly idListeners: Map<string, Set<Listener>> = new Map();

  getSelectedItems = (): Item[] => {
    return this.items;
  };

  isSelected = (id: string): boolean => {
    return this.itemsById.has(id);
  };

  setSelectedItems = (action: SetSelectedItemsAction): void => {
    const next =
      typeof action === "function"
        ? (action as (prev: Item[]) => Item[])(this.items)
        : action;

    if (next === this.items) {
      return;
    }

    const prevMap = this.itemsById;
    const nextMap = new Map<string, Item>();
    next.forEach((item) => nextMap.set(item.id, item));

    const changedIds = new Set<string>();
    prevMap.forEach((_, id) => {
      if (!nextMap.has(id)) changedIds.add(id);
    });
    nextMap.forEach((_, id) => {
      if (!prevMap.has(id)) changedIds.add(id);
    });

    // Bail out when no id was added or removed: callers sometimes pass a new
    // array reference with the same content (e.g. shift+click over a range
    // that is already fully selected). Keeping the previous reference avoids
    // waking up global listeners (selection bar, drag overlay, modals) for a
    // no-op change.
    if (changedIds.size === 0 && prevMap.size === nextMap.size) {
      return;
    }

    this.items = next;
    this.itemsById = nextMap;

    // Notify only the id listeners whose selection status actually changed.
    // Rows whose isSelected value stayed the same (true→true or false→false)
    // are not notified, so React bails out without re-rendering them.
    changedIds.forEach((id) => {
      const listeners = this.idListeners.get(id);
      if (listeners) listeners.forEach((l) => l());
    });

    this.globalListeners.forEach((l) => l());
  };

  clear = (): void => {
    if (this.items.length === 0) return;
    this.setSelectedItems([]);
  };

  subscribe = (listener: Listener): (() => void) => {
    this.globalListeners.add(listener);
    return () => {
      this.globalListeners.delete(listener);
    };
  };

  subscribeToId = (id: string, listener: Listener): (() => void) => {
    let set = this.idListeners.get(id);
    if (!set) {
      set = new Set();
      this.idListeners.set(id, set);
    }
    set.add(listener);
    return () => {
      const current = this.idListeners.get(id);
      if (!current) return;
      current.delete(listener);
      if (current.size === 0) this.idListeners.delete(id);
    };
  };
}

export const SelectionStoreContext = createContext<SelectionStore | undefined>(
  undefined,
);

export const useSelectionStore = (): SelectionStore => {
  const store = useContext(SelectionStoreContext);
  if (!store) {
    throw new Error(
      "useSelectionStore must be used within a SelectionStoreProvider",
    );
  }
  return store;
};

export const useSelectedItems = (): Item[] => {
  const store = useSelectionStore();
  return useSyncExternalStore(
    store.subscribe,
    store.getSelectedItems,
    store.getSelectedItems,
  );
};

export const useHasSelection = (): boolean => {
  const store = useSelectionStore();
  return useSyncExternalStore(
    store.subscribe,
    () => store.getSelectedItems().length > 0,
    () => store.getSelectedItems().length > 0,
  );
};

export const useSelectionCount = (): number => {
  const store = useSelectionStore();
  return useSyncExternalStore(
    store.subscribe,
    () => store.getSelectedItems().length,
    () => store.getSelectedItems().length,
  );
};

export const useIsItemSelected = (id: string): boolean => {
  const store = useSelectionStore();
  const subscribe = useCallback(
    (listener: Listener) => store.subscribeToId(id, listener),
    [store, id],
  );
  const getSnapshot = useCallback(() => store.isSelected(id), [store, id]);
  return useSyncExternalStore(subscribe, getSnapshot, getSnapshot);
};

export const useSetSelectedItems = (): ((
  action: SetSelectedItemsAction,
) => void) => {
  const store = useSelectionStore();
  return store.setSelectedItems;
};

/**
 * Creates a stable SelectionStore instance for the lifetime of the component.
 * Use together with `SelectionStoreContext.Provider` to scope a selection
 * (e.g. a nested embedded explorer inside a modal needs its own store,
 * independent from the global app-level selection).
 */
export const useCreateSelectionStore = (): SelectionStore => {
  const ref = useRef<SelectionStore | null>(null);
  if (ref.current === null) {
    ref.current = new SelectionStore();
  }
  return ref.current;
};
