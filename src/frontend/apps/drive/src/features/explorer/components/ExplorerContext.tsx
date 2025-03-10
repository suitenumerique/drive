import { SetStateAction, useContext, useState } from "react";
import { Dispatch } from "react";
import { useQuery } from "@tanstack/react-query";
import { Item } from "@/features/drivers/types";
import { createContext } from "react";
import { database } from "./database";
import { getDriver } from "@/features/config/Config";

export interface ExplorerContextType {
  selectedItemIds: Record<string, boolean>;
  setSelectedItemIds: Dispatch<SetStateAction<Record<string, boolean>>>;
  displayMode: "sdk" | "app";
  selectedItems: Item[];
  itemId: string;
  item: Item | undefined;
}

export const ExplorerContext = createContext<ExplorerContextType | undefined>(
  undefined
);

export const useExplorer = () => {
  const context = useContext(ExplorerContext);
  if (!context) {
    throw new Error("useExplorer must be used within an ExplorerProvider");
  }
  return context;
};

/**
 *
 * TODO:
 * - make router external as props onNavigate = {type, itemid}
 *J
 */
export const ExplorerProvider = ({
  children,
  displayMode = "app",
  itemId,
}: {
  children: React.ReactNode;
  displayMode: "sdk" | "app";
  itemId: string;
}) => {
  const [selectedItemIds, setSelectedItemIds] = useState<
    Record<string, boolean>
  >({});

  const getSelectedItems = () => {
    return database.filter((item) => selectedItemIds[item.id]);
  };

  const { data: item } = useQuery({
    queryKey: ["items", itemId],
    queryFn: () => getDriver().getItem(itemId),
  });

  return (
    <ExplorerContext.Provider
      value={{
        selectedItemIds,
        setSelectedItemIds,
        displayMode,
        selectedItems: getSelectedItems(),
        itemId,
        item,
      }}
    >
      {children}
    </ExplorerContext.Provider>
  );
};
