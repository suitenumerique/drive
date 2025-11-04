import { Button, useModal } from "@openfun/cunningham-react";
import {
  NavigationEventType,
  useGlobalExplorer,
} from "@/features/explorer/components/GlobalExplorerContext";
import {
  IconSize,
  useDropdownMenu,
  useTreeContext,
} from "@gouvfr-lasuite/ui-kit";
import { Item, TreeItem } from "@/features/drivers/types";
import { ItemIcon } from "@/features/explorer/components/icons/ItemIcon";
import createFolderSvg from "@/assets/icons/add_folder.svg";
import { EmbeddedExplorerGridBreadcrumbs } from "@/features/explorer/components/embedded-explorer/EmbeddedExplorerGridBreadcrumbs";
import { ExplorerCreateFolderModal } from "../modals/ExplorerCreateFolderModal";
import { ImportDropdown } from "../item-actions/ImportDropdown";
import { useTranslation } from "react-i18next";

export const AppExplorerBreadcrumbs = () => {
  const { item, onNavigate, treeIsInitialized } = useGlobalExplorer();
  const { t } = useTranslation();
  const createFolderModal = useModal();
  const importDropdown = useDropdownMenu();

  if (!item || !treeIsInitialized) {
    return null;
  }

  return (
    <>
      <div
        className="explorer__content__breadcrumbs"
        data-testid="explorer-breadcrumbs"
      >
        <EmbeddedExplorerGridBreadcrumbs
          currentItemId={item.id}
          showMenuLastItem={true}
          onGoBack={(item) => {
            onNavigate({
              type: NavigationEventType.ITEM,
              item,
            });
          }}
        />

        <div className="explorer__content__breadcrumbs__actions">
          <ImportDropdown
            importMenu={importDropdown}
            trigger={
              <Button
                variant="tertiary"
                size="small"
                onClick={() => {
                  importDropdown.setIsOpen(true);
                }}
              >
                {t("explorer.tree.import.label")}
              </Button>
            }
          />
          <Button
            icon={<img src={createFolderSvg.src} alt="Create Folder" />}
            variant="tertiary"
            size="small"
            onClick={() => {
              createFolderModal.open();
            }}
          />
        </div>
      </div>
      <ExplorerCreateFolderModal {...createFolderModal} parentId={item.id} />
    </>
  );
};

export const ExplorerBreadcrumbsMobile = () => {
  const treeContext = useTreeContext<TreeItem>();
  const { item, onNavigate, treeIsInitialized } = useGlobalExplorer();

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
              variant="bordered"
              color="neutral"
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
