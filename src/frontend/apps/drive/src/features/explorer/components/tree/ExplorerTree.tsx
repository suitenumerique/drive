import { useModal } from "@openfun/cunningham-react";
import { useTranslation } from "react-i18next";
import { itemsToTreeItems, useExplorer } from "../ExplorerContext";
import { Item, TreeItem } from "@/features/drivers/types";
import {
  HorizontalSeparator,
  OpenMap,
  TreeView,
  TreeViewDataType,
  TreeViewMoveResult,
  TreeViewNodeTypeEnum,
  useTreeContext,
} from "@gouvfr-lasuite/ui-kit";
import { useEffect, useRef, useState } from "react";
import { ExplorerTreeItem } from "./ExplorerTreeItem";
import { useMoveItems } from "../../api/useMoveItem";
import { ExplorerCreateFolderModal } from "../modals/ExplorerCreateFolderModal";
import { ExplorerCreateWorkspaceModal } from "../modals/workspaces/ExplorerCreateWorkspaceModal";
import { ExplorerTreeActions } from "./ExplorerTreeActions";
import { ExplorerTreeNav } from "./nav/ExplorerTreeNav";
import { addItemsMovedToast } from "../toasts/addItemsMovedToast";
import { ExplorerTreeMoveConfirmationModal } from "./ExplorerTreeMoveConfirmationModal";

export const ExplorerTree = () => {
  const { t } = useTranslation();
  const move = useMoveItems();
  const moveCallbackRef = useRef<() => void>(null);
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

  const createFolderModal = useModal();
  const createWorkspaceModal = useModal();

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
            const canDropOnParent = parent?.abilities.children_create ?? false;
            const activeItem = args.dragNodes[0].data.value as Item;
            const canDropActiveItem = activeItem.abilities.move;
            const canDropItem = canDropOnParent && canDropActiveItem;

            return (
              args.index === 0 &&
              args.parentNode?.willReceiveDrop === true &&
              canDropItem
            );
          }}
          renderNode={ExplorerTreeItem}
          rootNodeId={"root"}
        />
      )}

      <ExplorerTreeNav />

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
