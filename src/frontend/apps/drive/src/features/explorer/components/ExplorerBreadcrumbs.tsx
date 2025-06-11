import { Button } from "@openfun/cunningham-react";
import { NavigationEventType, useExplorer } from "./ExplorerContext";
import { IconSize, useTreeContext } from "@gouvfr-lasuite/ui-kit";
import { Item, TreeItem } from "@/features/drivers/types";
import { ItemIcon } from "./icons/ItemIcon";
import { ExplorerGridBreadcrumbs } from "./breadcrumbs/ExplorerGridBreadcrumbs";

export const ExplorerBreadcrumbs = () => {
  const {
    item,
    onNavigate,
    setRightPanelOpen,
    setRightPanelForcedItem,
    treeIsInitialized,
  } = useExplorer();

  if (!item || !treeIsInitialized) {
    return null;
  }

  return (
    <div className="explorer__content__breadcrumbs">
      <ExplorerGridBreadcrumbs
        buildWithTreeContext
        currentItemId={item.id}
        onGoBack={(item) => {
          onNavigate({
            type: NavigationEventType.ITEM,
            item,
          });
        }}
      />

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
              <ItemIcon item={workspace} size={IconSize.X_SMALL} />
              <span>{workspace.title}</span>
            </div>
            <div className="explorer__content__breadcrumbs--mobile__container__info__folder">
              {current.title}
            </div>
          </div>
        </div>
      ) : (
        <div className="explorer__content__breadcrumbs--mobile__workspace">
          <ItemIcon item={workspace as Item} size={IconSize.SMALL} />
          <span>{workspace.title}</span>
        </div>
      )}
    </div>
  );
};
