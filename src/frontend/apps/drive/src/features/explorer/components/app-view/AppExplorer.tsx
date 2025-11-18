import { Item } from "@/features/drivers/types";
import { createContext, useContext, useMemo } from "react";
import { ItemFilters } from "@/features/drivers/Driver";
import { EmbeddedExplorerGridActionsCellProps } from "@/features/explorer/components/embedded-explorer/EmbeddedExplorerGridActionsCell";
import { NavigationEvent } from "@/features/explorer/components/GlobalExplorerContext";
import { AppExplorerInner } from "./AppExplorerInner";
import { ContextMenu } from "@/features/ui/components/context-menu/ContextMenu";
import { useTranslation } from "react-i18next";

export interface AppExplorerProps {
  childrenItems?: Item[];
  gridActionsCell?: (
    params: EmbeddedExplorerGridActionsCellProps
  ) => React.ReactNode;
  disableItemDragAndDrop?: boolean;
  gridHeader?: React.ReactNode;
  selectionBarActions?: React.ReactNode;
  filters?: ItemFilters;
  onFiltersChange?: (filters: ItemFilters) => void;
  // Override the default onNavigate from ExplorerContext
  onNavigate?: (event: NavigationEvent) => void;
  disableAreaSelection?: boolean;
  canSelect?: (item: Item) => boolean;
  // Infinite scroll props
  hasNextPage?: boolean;
  isFetchingNextPage?: boolean;
  fetchNextPage?: () => void;
  isLoading?: boolean;
  isMinimalLayout?: boolean;
}

export type AppExplorerType = AppExplorerProps;

export const AppExplorerContext = createContext<AppExplorerType | undefined>(
  undefined
);

export const useAppExplorer = () => {
  const context = useContext(AppExplorerContext);
  if (!context) {
    throw new Error(
      "useAppExplorer must be used within an AppExplorerProvider"
    );
  }
  return context;
};

export const AppExplorer = (props: AppExplorerProps) => {
  const { t } = useTranslation();
  const contextMenuItems = useMemo(
    () => [
      {
        id: "open",
        label: "Open",
        onSelect: () => {
          console.log("open");
        },
      },
    ],
    []
  );
  return (
    <AppExplorerContext.Provider value={props}>
      <ContextMenu
        key={"toto"}
        items={contextMenuItems}
        ariaLabel={t("explorer.context_menu.aria_label", {
          defaultValue: `Actions pour toto`,
          item: "toto",
        })}
        shouldOpen={() => true}
        onOpen={(event) => {
          console.log("open global explorer");
        }}
      >
        <div>
          <AppExplorerInner {...props} />
        </div>
      </ContextMenu>
    </AppExplorerContext.Provider>
  );
};
