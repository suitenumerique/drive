import { useModal } from "@openfun/cunningham-react";
import { useTranslation } from "react-i18next";
import {
  itemsToTreeItems,
  NavigationEventType,
  useExplorer,
} from "../ExplorerContext";
import { Item, TreeItem } from "@/features/drivers/types";
import {
  HorizontalSeparator,
  OpenMap,
  TreeDataItem,
  TreeView,
  TreeViewDataType,
  TreeViewMoveResult,
  TreeViewNodeTypeEnum,
  useTreeContext,
} from "@gouvfr-lasuite/ui-kit";
import { useEffect, useState } from "react";
import { ExplorerTreeItem, ExplorerTreeItemIcon } from "./ExplorerTreeItem";
import { useMoveItems } from "../../api/useMoveItem";
import { ExplorerCreateFolderModal } from "../modals/ExplorerCreateFolderModal";
import { ExplorerCreateWorkspaceModal } from "../modals/workspaces/ExplorerCreateWorkspaceModal";
import { ExplorerTreeActions } from "./ExplorerTreeActions";
import { ExplorerTreeNav } from "./nav/ExplorerTreeNav";
import { addItemsMovedToast } from "../toasts/addItemsMovedToast";
import { ExplorerTreeMoveConfirmationModal } from "./ExplorerTreeMoveConfirmationModal";
import { ExplorerSearchModal } from "../modals/search/ExplorerSearchModal";
import { canDrop } from "../ExplorerDndProvider";
import { LanguagePicker } from "@/features/layouts/components/header/Header";
import { LogoutButton } from "@/features/auth/components/LogoutButton";
import React from "react";
import clsx from "clsx";

export const ExplorerTree = () => {
  const { t, i18n } = useTranslation();
  const move = useMoveItems();
  const moveConfirmationModal = useModal();
  const [moveState, setMoveState] = useState<{
    moveCallback: () => void;
    sourceItem: Item;
    targetItem: Item;
  }>();

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
    if (!firstLevelItems) {
      return;
    }
    // If we are on an item page, we want to wait for the tree request to be resolved in order to build the tree.
    if (itemId && !treeItem) {
      return;
    }

    const firstLevelItems_: Item[] = firstLevelItems ?? [];

    // On some route no treeItem is provided, like on the trash route.
    if (treeItem) {
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
    const mainWorkspace = firstLevelTreeItems_[mainWorkspaceIndex] as Item;

    mainWorkspace.title = t("explorer.workspaces.mainWorkspace");

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

  // When the language changes, we update the tree titles to be sure they are translated
  useEffect(() => {
    if (!treeIsInitialized) {
      return;
    }

    treeContext?.treeData.updateNode("PERSONAL_SPACE", {
      headerTitle: t("explorer.workspaces.mainWorkspace"),
    });

    treeContext?.treeData.updateNode("SHARED_SPACE", {
      headerTitle: t("explorer.tree.sharedSpace"),
    });
  }, [i18n.language, t, treeIsInitialized]);

  const createFolderModal = useModal();
  const createWorkspaceModal = useModal();
  const searchModal = useModal();

  const handleMove = (result: TreeViewMoveResult) => {
    move.mutate(
      {
        ids: [result.sourceId],
        parentId: result.targetModeId,
        oldParentId: result.oldParentId ?? itemId,
      },
      {
        onSuccess: () => {
          addItemsMovedToast(1);
        },
      }
    );
  };

  return (
    <div className="explorer__tree">
      <ExplorerTreeActions
        openCreateFolderModal={createFolderModal.open}
        openCreateWorkspaceModal={createWorkspaceModal.open}
      />
      <HorizontalSeparator withPadding={false} />

      <ExplorerTreeMobile />

      {initialOpenState && (
        <TreeView
          selectedNodeId={itemId}
          initialOpenState={initialOpenState}
          afterMove={handleMove}
          beforeMove={(moveResult, moveCallback) => {
            // TODO: this comes from the tree in the ui-kit, it needs to be explained in the documentation
            if (!moveResult.newParentId || !moveResult.oldParentId) {
              return;
            }

            const parent = treeContext?.treeData.getNode(
              moveResult.newParentId
            ) as Item | undefined;
            const oldParent = treeContext?.treeData.getNode(
              moveResult.oldParentId
            ) as Item | undefined;

            if (!parent || !oldParent) {
              return;
            }

            const oldParentPath = oldParent.path.split(".");
            const parentPath = parent.path.split(".");

            // If the workspace is the same as the old workspace, we don't need to confirm the move
            if (parentPath[0] === oldParentPath[0]) {
              moveCallback();
              return;
            }

            setMoveState({
              moveCallback,
              sourceItem: oldParent,
              targetItem: parent,
            });
            moveConfirmationModal.open();
          }}
          canDrag={(args) => {
            const item = args.value as TreeItem;
            if (item.nodeType !== TreeViewNodeTypeEnum.NODE) {
              return false;
            }

            return item.abilities.move;
          }}
          canDrop={(args) => {
            const parent = args.parentNode?.data.value as Item | undefined;
            const activeItem = args.dragNodes[0].data.value as Item;
            const canDropResult = parent ? canDrop(activeItem, parent) : true;

            return (
              args.index === 0 &&
              args.parentNode?.willReceiveDrop === true &&
              canDropResult
            );
          }}
          renderNode={ExplorerTreeItem}
          rootNodeId={"root"}
        />
      )}

      <ExplorerTreeNav />

      <div className="explorer__tree__mobile-navs">
        <HorizontalSeparator />

        <div className="explorer__tree__mobile-navs__inner">
          <LogoutButton />
          <LanguagePicker />
        </div>
      </div>

      <ExplorerSearchModal {...searchModal} />
      <ExplorerCreateFolderModal {...createFolderModal} parentId={itemId} />
      <ExplorerCreateWorkspaceModal {...createWorkspaceModal} />
      {moveState && moveConfirmationModal.isOpen && (
        <ExplorerTreeMoveConfirmationModal
          isOpen={moveConfirmationModal.isOpen}
          onClose={() => {
            moveConfirmationModal.close();
            setMoveState(undefined);
          }}
          sourceItem={moveState.sourceItem}
          targetItem={moveState.targetItem}
          onMove={() => {
            moveState.moveCallback();
            moveConfirmationModal.close();
          }}
        />
      )}
    </div>
  );
};

export const ExplorerTreeMobile = () => {
  const treeContext = useTreeContext<TreeItem>();
  const { item, onNavigate, setIsLeftPanelOpen } = useExplorer();

  const nodes = treeContext?.treeData.nodes;

  if (!nodes) {
    return null;
  }

  const renderNode = (node: TreeDataItem<TreeItem>) => {
    const isSelected = item?.id === node.value.id;
    const type = node.value.nodeType;
    if (type === TreeViewNodeTypeEnum.NODE) {
      return (
        <div
          className={clsx(
            "explorer__tree__mobile__item",
            "explorer__tree__mobile__node",
            {
              "explorer__tree__mobile__node--selected": isSelected,
            }
          )}
          onClick={() => {
            onNavigate({
              type: NavigationEventType.ITEM,
              item: node.value as Item,
            });
            setIsLeftPanelOpen(false);
          }}
        >
          <ExplorerTreeItemIcon item={node.value} size={24} />
          <span>{node.value.title}</span>
        </div>
      );
    }

    if (type === TreeViewNodeTypeEnum.TITLE) {
      return (
        <div className="explorer__tree__mobile__item explorer__tree__mobile__title">
          {node.value.headerTitle}
        </div>
      );
    }

    if (type === TreeViewNodeTypeEnum.SEPARATOR) {
      return <HorizontalSeparator withPadding={true} />;
    }

    return null;
  };

  return (
    <div className="explorer__tree__mobile">
      {nodes.map((node) => (
        <React.Fragment key={node.key}>{renderNode(node)}</React.Fragment>
      ))}
    </div>
  );
};
