import { useModal } from "@openfun/cunningham-react";
import { useTranslation } from "react-i18next";
import {
  NavigationEventType,
  useGlobalExplorer,
} from "../GlobalExplorerContext";
import { Item, TreeItem } from "@/features/drivers/types";
import {
  HorizontalSeparator,
  IconSize,
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
import { canDrop } from "../ExplorerDndProvider";
import React from "react";
import clsx from "clsx";
import { LeftPanelMobile } from "@/features/layouts/components/left-panel/LeftPanelMobile";
import { WorkspaceCategory } from "../../constants";

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

  const { itemId, treeIsInitialized } = useGlobalExplorer();

  // Initialize the opened nodes when the tree is initialized.
  useEffect(() => {
    if (!treeIsInitialized) {
      return;
    }
    if (initialOpenState) {
      return;
    }
    const initialOpenedNodes: OpenMap = {};

    // Browse the data to initialize the opened nodes
    const openLoadedNodes = (
      items: TreeDataItem<TreeViewDataType<TreeItem>>[]
    ) => {
      items.forEach((item) => {
        if (
          item.value.childrenCount &&
          item.value.childrenCount > 0 &&
          item.value.children &&
          item.value.children.length > 0
        ) {
          initialOpenedNodes[item.value.id] = true;

          if (item.value.children) {
            openLoadedNodes(item.children!);
          }
        }
      });
    };

    const treeData = treeContext!.treeData.nodes;
    openLoadedNodes(treeData);
    setInitialOpenState(initialOpenedNodes);
  }, [treeContext?.treeData.nodes]);

  // When the language changes, we update the tree titles to be sure they are translated
  useEffect(() => {
    if (!treeIsInitialized) {
      return;
    }

    const treeData = treeContext?.treeData;

    // No main workspace when being anon on a public workspace.
    if (treeData?.getNode("PERSONAL_SPACE")) {
      treeData?.updateNode("PERSONAL_SPACE", {
        headerTitle: t("explorer.workspaces.mainWorkspace"),
      });
    }

    if (treeData?.getNode(WorkspaceCategory.SHARED_SPACE)) {
      treeData.updateNode(WorkspaceCategory.SHARED_SPACE, {
        headerTitle: t("explorer.tree.shared_space"),
      });
    }

    if (treeData?.getNode(WorkspaceCategory.PUBLIC_SPACE)) {
      treeData.updateNode(WorkspaceCategory.PUBLIC_SPACE, {
        headerTitle: t("explorer.tree.public_space"),
      });
    }
  }, [i18n.language, t, treeIsInitialized]);

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

      <ExplorerTreeMobile />

      {initialOpenState && (
        <TreeView
          // selectedNodeId={itemId}

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

            return item.abilities?.move ?? false;
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
        <LeftPanelMobile />
      </div>
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
  const { item, onNavigate, setIsLeftPanelOpen } = useGlobalExplorer();

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
          <ExplorerTreeItemIcon item={node.value} size={IconSize.X_SMALL} />
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
