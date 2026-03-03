import {
  createContext,
  ReactNode,
  useCallback,
  useContext,
  useState,
} from "react";
import { ColumnPreferences, ColumnType } from "../types/columns";
import {
  ColumnPreferencesStore,
  LocalStorageColumnPreferencesStore,
} from "../store/columnPreferences";

type ColumnPreferencesContextType = {
  prefs: ColumnPreferences;
  setColumn: (slot: "column1" | "column2", type: ColumnType) => void;
};

const ColumnPreferencesContext = createContext<
  ColumnPreferencesContextType | undefined
>(undefined);

type ColumnPreferencesProviderProps = {
  store?: ColumnPreferencesStore;
  children: ReactNode;
};

export function ColumnPreferencesProvider({
  store: storeProp,
  children,
}: ColumnPreferencesProviderProps) {
  const [store] = useState<ColumnPreferencesStore>(
    () => storeProp ?? new LocalStorageColumnPreferencesStore(),
  );
  const [prefs, setPrefsState] = useState<ColumnPreferences>(() => store.get());

  const setColumn = useCallback(
    (slot: "column1" | "column2", type: ColumnType) => {
      setPrefsState((prev) => {
        const next = { ...prev, [slot]: type };
        store.set(next);
        return next;
      });
    },
    [store],
  );

  return (
    <ColumnPreferencesContext.Provider value={{ prefs, setColumn }}>
      {children}
    </ColumnPreferencesContext.Provider>
  );
}

export function useColumnPreferences(): ColumnPreferencesContextType {
  const context = useContext(ColumnPreferencesContext);
  if (!context) {
    throw new Error(
      "useColumnPreferences must be used within a ColumnPreferencesProvider",
    );
  }
  return context;
}
