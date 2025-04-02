import { Button, useModal } from "@openfun/cunningham-react";
import { useTranslation } from "react-i18next";
import { itemsToTreeItems, useExplorer } from "../ExplorerContext";
import { Item, TreeItem } from "@/features/drivers/types";
import {
  DropdownMenu,
  HorizontalSeparator,
  OpenMap,
  TreeView,
  TreeViewDataType,
  TreeViewMoveResult,
  TreeViewNodeTypeEnum,
  useDropdownMenu,
  useTreeContext,
} from "@gouvfr-lasuite/ui-kit";
import { useEffect, useState } from "react";
import { ExplorerTreeItem } from "./ExplorerTreeItem";
import { useMoveItems } from "../../api/useMoveItem";
import { ExplorerCreateFolderModal } from "../modals/ExplorerCreateFolderModal";
import uploadFileSvg from "@/assets/icons/upload_file.svg";
import uploadFolderSvg from "@/assets/icons/upload_folder.svg";

export const ExplorerTree = () => {
  const { t } = useTranslation();
  const move = useMoveItems();
  const dropdownMenu = useDropdownMenu();

  const treeContext = useTreeContext<TreeItem>();
  const [initialOpenState, setInitialOpenState] = useState<OpenMap | undefined>(
    undefined
  );

  const {
    tree: treeItem,
    firstLevelItems,
    itemId,

    setTreeIsInitialized,
    treeIsInitialized,
  } = useExplorer();

  useEffect(() => {
    if (!treeItem || !firstLevelItems) {
      return;
    }

    const firstLevelItems_: Item[] = firstLevelItems ?? [];

    const treeItemIndex = firstLevelItems_.findIndex(
      (item) => item.id === treeItem.id
    );

    if (treeItemIndex !== -1) {
      // as we need to make two requests to retrieve the items and the minimal tree based
      // on where we invoke the tree, we replace the root of the invoked tree in the array
      firstLevelItems_[treeItemIndex] = treeItem;
    } else {
      // Otherwise we add it to the beginning of the array
      firstLevelItems_.unshift(treeItem);
    }

    const firstLevelTreeItems_: TreeItem[] = itemsToTreeItems(firstLevelItems_);

    const mainWorkspaceIndex = firstLevelTreeItems_.findIndex((item) => {
      if (item.nodeType === TreeViewNodeTypeEnum.NODE) {
        return item.main_workspace;
      }
      return false;
    });

    const items: TreeViewDataType<TreeItem>[] = [];

    const initialOpenedNodes: OpenMap = {};

    // Browse the data to initialize the opened nodes
    const openLoadedNodes = (items: TreeItem[]) => {
      items.forEach((item) => {
        if (
          item.childrenCount &&
          item.childrenCount > 0 &&
          item.children &&
          item.children.length > 0
        ) {
          initialOpenedNodes[item.id] = true;

          if (item.children) {
            openLoadedNodes(item.children);
          }
        }
      });
    };

    openLoadedNodes(firstLevelTreeItems_);
    setInitialOpenState(initialOpenedNodes);

    // We start to build the tree
    const personalWorkspaceNode: TreeViewDataType<TreeItem> = {
      id: "PERSONAL_SPACE",
      nodeType: TreeViewNodeTypeEnum.TITLE,
      headerTitle: t("explorer.tree.personalSpace"),
    };

    // We add the personal workspace node and the main workspace node
    items.push(personalWorkspaceNode);
    items.push(firstLevelTreeItems_[mainWorkspaceIndex]);

    if (firstLevelTreeItems_.length > 1) {
      // We add a separator and the shared space node
      const separator: TreeViewDataType<TreeItem> = {
        id: "SEPARATOR",
        nodeType: TreeViewNodeTypeEnum.SEPARATOR,
      };

      const sharedSpace: TreeViewDataType<TreeItem> = {
        id: "SHARED_SPACE",
        nodeType: TreeViewNodeTypeEnum.TITLE,
        headerTitle: t("explorer.tree.sharedSpace"),
      };

      items.push(separator);
      items.push(sharedSpace);

      // We remove the main workspace node and add the rest of the nodes
      firstLevelTreeItems_.splice(mainWorkspaceIndex, 1);
      items.push(...firstLevelTreeItems_);
    }

    treeContext?.treeData.resetTree(items);
  }, [treeItem, firstLevelItems]);

  useEffect(() => {
    if (initialOpenState && !treeIsInitialized) {
      setTreeIsInitialized(true);
    }
  }, [initialOpenState, setTreeIsInitialized, treeIsInitialized]);

  const createFolderModal = useModal();

  const handleMove = (result: TreeViewMoveResult) => {
    move.mutate({
      ids: [result.sourceId],
      parentId: result.targetModeId,
      oldParentId: result.oldParentId ?? itemId,
    });
  };

  return (
    <div className="explorer__tree">
      <div className="explorer__tree__actions">
        <div className="explorer__tree__actions__left">
          <Button
            icon={<span className="material-icons">add</span>}
            onClick={createFolderModal.open}
          >
            {t("explorer.tree.createFolder")}
          </Button>
          <DropdownMenu
            options={[
              {
                icon: <img src={uploadFileSvg.src} alt="" />,
                label: t("explorer.tree.import.files"),
                value: "info",
                callback: () => {
                  document.getElementById("import-files")?.click();
                },
              },
              {
                icon: <img src={uploadFolderSvg.src} alt="" />,
                label: t("explorer.tree.import.folders"),
                value: "info",
                callback: () => {
                  document.getElementById("import-folders")?.click();
                },
              },
            ]}
            {...dropdownMenu}
            onOpenChange={dropdownMenu.setIsOpen}
          >
            <Button
              color="secondary"
              onClick={() => dropdownMenu.setIsOpen(true)}
            >
              {t("explorer.tree.import.label")}
            </Button>
          </DropdownMenu>
        </div>
        <Button
          color="primary-text"
          aria-label={t("explorer.tree.search")}
          icon={<span className="material-icons">search</span>}
        ></Button>
      </div>
      <HorizontalSeparator withPadding={false} />

      {initialOpenState && (
        <TreeView
          selectedNodeId={itemId}
          initialOpenState={initialOpenState}
          afterMove={handleMove}
          canDrop={(args) => {
            // To only allow dropping on a node and not between nodes
            return (
              args.index === 0 && args.parentNode?.willReceiveDrop === true
            );
          }}
          renderNode={ExplorerTreeItem}
          rootNodeId={"root"}
        />
      )}

      <ExplorerCreateFolderModal {...createFolderModal} />
    </div>
  );
};
