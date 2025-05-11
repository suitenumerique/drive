import { Breadcrumbs } from "@/features/ui/components/breadcrumbs/Breadcrumbs";
import { Button } from "@openfun/cunningham-react";
import workspaceLogo from "@/assets/workspace_logo.svg";
import { NavigationEventType, useExplorer } from "./ExplorerContext";
import { useMemo } from "react";
import { TreeViewNodeTypeEnum, useTreeContext } from "@gouvfr-lasuite/ui-kit";
import { Item, TreeItem } from "@/features/drivers/types";
import workspaceIcon from "@/assets/tree/workspace.svg";
import mainWorkspaceIcon from "@/assets/tree/main-workspace.svg";
import { ExplorerTreeItemIcon } from "./tree/ExplorerTreeItem";

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

export const ExplorerBreadcrumbsMobile = () => {
  const treeContext = useTreeContext<TreeItem>();
  const { item, onNavigate, treeIsInitialized } = useExplorer();

  const getItems = () => {
    if (!item) {
      return null;
    }

    const nodes = treeContext?.treeData.nodes ?? [];

    const ancestors: Item[] =
      nodes.length > 0
        ? (treeContext?.treeData.getAncestors(item.id) as Item[])
        : [];

    if (ancestors.length === 0) {
      return null;
    }

    const workspace = ancestors[0];
    const current = item.id === workspace.id ? null : item;
    const parent = current ? ancestors[ancestors.length - 2] : null;
    return {
      workspace,
      current,
      parent,
    };
  };

  if (!item || !treeIsInitialized) {
    return null;
  }

  const items = getItems();
  if (!items) {
    return null;
  }

  const { workspace, parent, current } = items;

  return (
    <div className="explorer__content__breadcrumbs--mobile">
      {current ? (
        <div className="explorer__content__breadcrumbs--mobile__container">
          <div className="explorer__content__breadcrumbs--mobile__container__actions">
            <Button
              color="tertiary"
              icon={<span className="material-icons">chevron_left</span>}
              onClick={() => {
                onNavigate({
                  type: NavigationEventType.ITEM,
                  item: parent as Item,
                });
              }}
            />
          </div>
          <div className="explorer__content__breadcrumbs--mobile__container__info">
            <div className="explorer__content__breadcrumbs--mobile__container__info__title">
              <ExplorerTreeItemIcon item={workspace} size={16} />
              <span>{workspace.title}</span>
            </div>
            <div className="explorer__content__breadcrumbs--mobile__container__info__folder">
              {current.title}
            </div>
          </div>
        </div>
      ) : (
        <div className="explorer__content__breadcrumbs--mobile__workspace">
          <ExplorerTreeItemIcon item={workspace} size={24} />
          <span>{workspace.title}</span>
        </div>
      )}
    </div>
  );
};
