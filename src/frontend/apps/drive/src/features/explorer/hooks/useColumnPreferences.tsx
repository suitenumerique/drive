import { createContext, ReactNode, useCallback, useContext, useState } from "react";
import {
  ColumnPreferences,
  ColumnType,
  DEFAULT_COLUMN_PREFERENCES,
} from "../types/columns";
import { useAuth } from "@/features/auth/Auth";
import { getDriver } from "@/features/config/Config";

type ColumnPreferencesContextType = {
  prefs: ColumnPreferences;
  setColumn: (slot: "column1" | "column2", type: ColumnType) => void;
};

const ColumnPreferencesContext = createContext<
  ColumnPreferencesContextType | undefined
>(undefined);

export function ColumnPreferencesProvider({
  children,
}: {
  children: ReactNode;
}) {
  const { user, refreshUser } = useAuth();
  const driver = getDriver();

  const [prefs, setPrefsState] = useState<ColumnPreferences>(
    () => user?.column_preferences ?? DEFAULT_COLUMN_PREFERENCES,
  );

  const setColumn = useCallback(
    (slot: "column1" | "column2", type: ColumnType) => {
      setPrefsState((prev) => {
        const next = { ...prev, [slot]: type };
        if (user) {
          driver
            .updateUser({ id: user.id, column_preferences: next })
            .then(() => {
              void refreshUser?.();
            });
        }
        return next;
      });
    },
    [user, driver, refreshUser],
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
