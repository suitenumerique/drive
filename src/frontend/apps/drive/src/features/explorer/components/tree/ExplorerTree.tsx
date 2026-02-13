import { useModal } from "@gouvfr-lasuite/cunningham-react";
import { useTranslation } from "react-i18next";
import { useGlobalExplorer } from "../GlobalExplorerContext";
import { Item, TreeItem } from "@/features/drivers/types";
import {
  DefaultRoute,
  getDefaultRoute,
  ORDERED_DEFAULT_ROUTES,
} from "@/utils/defaultRoutes";
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
import { useCallback, useEffect, useMemo, useState } from "react";
import { ExplorerTreeItem } from "./ExplorerTreeItem";
import { useMoveItems } from "../../api/useMoveItem";
import { ExplorerCreateFolderModal } from "../modals/ExplorerCreateFolderModal";
import { ExplorerTreeActions } from "./ExplorerTreeActions";
import { ExplorerTreeNav } from "./nav/ExplorerTreeNav";
import { addItemsMovedToast } from "../toasts/addItemsMovedToast";
import { ExplorerTreeMoveConfirmationModal } from "./ExplorerTreeMoveConfirmationModal";
import { canDrop } from "../ExplorerDndProvider";
import React from "react";
import { LeftPanelMobile } from "@/features/layouts/components/left-panel/LeftPanelMobile";
import { useAuth } from "@/features/auth/Auth";
import { ExplorerTreeNavItem } from "./nav/ExplorerTreeNavItem";
import { useRouter } from "next/router";

export const ExplorerTree = () => {
  const move = useMoveItems();
  const moveConfirmationModal = useModal();
  const router = useRouter();
  const [moveState, setMoveState] = useState<{
    moveCallback: () => void;
    sourceItem: Item;
    targetItem: Item;
  }>();

  const treeContext = useTreeContext<TreeItem>();
  const [initialOpenState, setInitialOpenState] = useState<OpenMap | undefined>(
    undefined,
  );

  const { itemId, treeIsInitialized } = useGlobalExplorer();
  const defaultSelectedNodeId = useMemo(() => {
    const defaultRoute = getDefaultRoute(router.pathname);
    if (defaultRoute) {
      return defaultRoute.id;
    }
    return itemId;
  }, [itemId, router.pathname]);

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
      items: TreeDataItem<TreeViewDataType<TreeItem>>[],
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

  const createFolderModal = useModal();

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
      },
    );
  };

  return (
    <div className="explorer__tree">
      <ExplorerTreeActions openCreateFolderModal={createFolderModal.open} />
      <HorizontalSeparator withPadding={false} />
      <ExplorerTreeNavDefault />
      
      {initialOpenState && (
        <TreeView
          selectedNodeId={defaultSelectedNodeId}
          afterMove={handleMove}
          beforeMove={(moveResult, moveCallback) => {
            // TODO: this comes from the tree in the ui-kit, it needs to be explained in the documentation
            if (!moveResult.newParentId || !moveResult.oldParentId) {
              return;
            }

            const parent = treeContext?.treeData.getNode(
              moveResult.newParentId,
            ) as Item | undefined;
            const oldParent = treeContext?.treeData.getNode(
              moveResult.oldParentId,
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
          paddingTop={0}
          canDrop={(args) => {
            const parent = args.parentNode?.data.value as Item | undefined;
            const activeItem = args.dragNodes[0].data.value as Item;
            const canDropResult = parent ? canDrop(activeItem, parent) : true;

            const result =
              args.index === 0 &&
              args.parentNode?.willReceiveDrop === true &&
              canDropResult;

            return result;
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

type ExplorerTreeNavNode = {
  id: string;
  label: string;
  route: string;
  icon: React.ReactNode | string;
};

export const ExplorerTreeNavDefault = () => {
  const { t } = useTranslation();
  const { user } = useAuth();
  const [nodes, setNodes] = useState<ExplorerTreeNavNode[]>([]);

  const initTree = useCallback(async () => {
    if (!user) {
      return;
    }

    const nodes: ExplorerTreeNavNode[] = ORDERED_DEFAULT_ROUTES.filter(
      (route) => route.id !== DefaultRoute.FAVORITES,
    ).map((route) => ({
      id: route.id,
      label: t(route.label),
      route: route.route,
      icon: <route.icon size={IconSize.SMALL} />,
    }));

    setNodes(nodes);
  }, [user, t]);

  useEffect(() => {
    initTree();
  }, [initTree]);

  if (!nodes) {
    return null;
  }

  return (
    <div className="explorer__tree__nav">
      {nodes.map((node) => (
        <ExplorerTreeNavItem key={node.id} {...node} />
      ))}
    </div>
  );
};
