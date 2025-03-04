import { Item } from "@/features/drivers/types";
import {
  useState,
  createContext,
  useContext,
  Dispatch,
  SetStateAction,
} from "react";
import { database } from "./database";
import { ExplorerInner } from "./ExplorerInner";

interface ExplorerContextType {
  selectedItems: Record<string, boolean>;
  setSelectedItems: Dispatch<SetStateAction<Record<string, boolean>>>;
  displayMode: "sdk" | "app";
  getSelectedItems: () => Item[];
}

const ExplorerContext = createContext<ExplorerContextType | undefined>(
  undefined
);

export const useExplorer = () => {
  const context = useContext(ExplorerContext);
  if (!context) {
    throw new Error("useExplorer must be used within an ExplorerProvider");
  }
  return context;
};

export const Explorer = ({
  itemId,
  displayMode = "app",
}: {
  itemId: string;
  displayMode: "sdk" | "app";
}) => {
  const [selectedItems, setSelectedItems] = useState<Record<string, boolean>>(
    {}
  );

  const getSelectedItems = () => {
    return database.filter((item) => selectedItems[item.id]);
  };

  return (
    <ExplorerContext.Provider
      value={{
        selectedItems,
        setSelectedItems,
        displayMode,
        getSelectedItems,
      }}
    >
      <ExplorerInner />
    </ExplorerContext.Provider>
  );
};
