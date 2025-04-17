import { Breadcrumbs } from "@/features/ui/components/breadcrumbs/Breadcrumbs";
import { Button } from "@openfun/cunningham-react";
import workspaceLogo from "@/assets/workspace_logo.svg";
import { NavigationEventType, useExplorer } from "./ExplorerContext";
import { useMemo } from "react";
import { TreeViewNodeTypeEnum, useTreeContext } from "@gouvfr-lasuite/ui-kit";
import { TreeItem } from "@/features/drivers/types";

export const ExplorerBreadcrumbs = () => {
  const treeContext = useTreeContext<TreeItem>();
  const {
    item,
    onNavigate,
    setRightPanelOpen,
    setRightPanelForcedItem,
    treeIsInitialized,
  } = useExplorer();

  const getBreadcrumbsItems = () => {
    if (!item) {
      return [];
    }

    const nodes = treeContext?.treeData.nodes ?? [];

    const ancestors: TreeItem[] =
      nodes.length > 0
        ? (treeContext?.treeData.getAncestors(item.id) as TreeItem[])
        : [];

    return ancestors.map((ancestor, index) => {
      return {
        content: (
          <button
            onClick={(e) => {
              e.preventDefault();
              onNavigate({
                type: NavigationEventType.ITEM,
                item: ancestor,
              });
            }}
            className="c__breadcrumbs__button"
          >
            {index === 0 && <img src={workspaceLogo.src} alt="Lasuite" />}
            {/**
             * This is due to the TreeViewDataType<T> type from the ui-kit. Indeed, the type T is only available for the NODE type.
             * So if we don't test for it, we don't have access to the title property
             **/}
            {ancestor.nodeType === TreeViewNodeTypeEnum.NODE && (
              <span>{ancestor.title}</span>
            )}
          </button>
        ),
      };
    });
  };

  const breadcrumbsItems = useMemo(
    () => getBreadcrumbsItems(),
    [item, treeIsInitialized]
  );

  if (!item || !treeIsInitialized) {
    return null;
  }

  return (
    <div className="explorer__content__breadcrumbs">
      <Breadcrumbs items={breadcrumbsItems} />
      <div className="explorer__content__breadcrumbs__actions">
        <Button
          icon={<span className="material-icons">info</span>}
          color="primary-text"
          onClick={() => {
            setRightPanelOpen(true);
            setRightPanelForcedItem(item);
          }}
        />
      </div>
    </div>
  );
};
