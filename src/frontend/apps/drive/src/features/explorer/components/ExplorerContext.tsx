import { SetStateAction, useContext, useEffect, useState } from "react";
import { Dispatch } from "react";
import { useQuery } from "@tanstack/react-query";
import { Item, ItemTreeItem } from "@/features/drivers/types";
import { createContext } from "react";
import { getDriver } from "@/features/config/Config";

export interface ExplorerContextType {
  selectedItemIds: Record<string, boolean>;
  setSelectedItemIds: Dispatch<SetStateAction<Record<string, boolean>>>;
  displayMode: "sdk" | "app";
  selectedItems: Item[];
  itemId: string;
  item: Item | undefined;
  children: Item[] | undefined;
  tree: Item | undefined;
  onNavigate: (event: NavigationEvent) => void;
  initialId: string | undefined;
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

export enum NavigationEventType {
  ITEM,
}

export type NavigationEvent = {
  type: NavigationEventType.ITEM;
  item: Item | ItemTreeItem;
};

export const ExplorerProvider = ({
  children,
  displayMode = "app",
  itemId,
  onNavigate,
}: {
  children: React.ReactNode;
  displayMode: "sdk" | "app";
  itemId: string;
  onNavigate: (event: NavigationEvent) => void;
}) => {
  const [selectedItemIds, setSelectedItemIds] = useState<
    Record<string, boolean>
  >({});

  const [initialId, setInitialId] = useState<string | undefined>(itemId);

  useEffect(() => {
    if (!initialId) {
      setInitialId(itemId);
    }
  }, [itemId]);

  const { data: item } = useQuery({
    queryKey: ["items", itemId],
    queryFn: () => getDriver().getItem(itemId),
  });

  const { data: itemChildren } = useQuery({
    queryKey: ["items", itemId, "children"],
    queryFn: () => getDriver().getChildren(itemId),
  });

  const { data: tree } = useQuery({
    queryKey: ["items", initialId, "tree"],
    queryFn: () => {
      if (!initialId) {
        return undefined;
      }
      return getDriver().getTree(initialId);
    },
  });

  const getSelectedItems = () => {
    return itemChildren
      ? itemChildren.filter((item) => selectedItemIds[item.id])
      : [];
  };

  return (
    <ExplorerContext.Provider
      value={{
        selectedItemIds,
        setSelectedItemIds,
        displayMode,
        selectedItems: getSelectedItems(),
        itemId,
        initialId,
        item,
        tree,
        children: itemChildren,
        onNavigate,
      }}
    >
      {children}
    </ExplorerContext.Provider>
  );
};
