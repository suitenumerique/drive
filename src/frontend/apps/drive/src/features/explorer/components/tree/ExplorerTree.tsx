import { useModal } from "@openfun/cunningham-react";
import { useTranslation } from "react-i18next";
import publicSpaceIcon from "@/assets/folder/folder-tiny-public.svg";
import sharedSpaceIcon from "@/assets/folder/folder-tiny-shared.svg";
import folderPersonalIcon from "@/assets/folder/folder-tiny-perso.svg";
import { useGlobalExplorer } from "../GlobalExplorerContext";
import { Item, TreeItem, WorkspaceType } from "@/features/drivers/types";
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
import { useCallback, useEffect, useMemo, useState } from "react";
import { ExplorerTreeItem } from "./ExplorerTreeItem";
import { useMoveItems } from "../../api/useMoveItem";
import { ExplorerCreateFolderModal } from "../modals/ExplorerCreateFolderModal";
import {
  ExplorerCreateFileModal,
  ExplorerCreateFileType,
} from "../modals/ExplorerCreateFileModal";
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
import { getDriver } from "@/features/config/Config";
import { useAuth } from "@/features/auth/Auth";
import { useRouter } from "next/router";

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
  const [createFileModalType, setCreateFileModalType] =
    useState<ExplorerCreateFileType>(ExplorerCreateFileType.DOC);
  const createFileModal = useModal();
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
        openCreateFileModal={(type: ExplorerCreateFileType) => {
          createFileModal.open();
          setCreateFileModalType(type);
        }}
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
      <ExplorerCreateFileModal
        {...createFileModal}
        parentId={itemId}
        type={createFileModalType}
      />
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

type ExplorerTreeMobileNode = {
  id: string;
  label: string;
  route: string;
  icon: string;
};

export const ExplorerTreeMobile = () => {
  const { t } = useTranslation();
  const router = useRouter();
  const { user } = useAuth();
  const { setIsLeftPanelOpen, mobileNodesRefreshTrigger } = useGlobalExplorer();
  const [nodes, setNodes] = useState<ExplorerTreeMobileNode[]>([]);
  const driver = useMemo(() => getDriver(), []);

  const initTree = useCallback(async () => {
    if (!user) {
      return;
    }
    const mainWorkspace = user.main_workspace;
    const sharedWorkspaces = await driver.getItems({
      workspaces: WorkspaceType.SHARED,
      page: 1,
    });
    const publicWorkspaces = await driver.getItems({
      workspaces: WorkspaceType.PUBLIC,
      page: 1,
    });

    const nodes: ExplorerTreeMobileNode[] = [
      {
        id: mainWorkspace.id,
        label: t("explorer.workspaces.mainWorkspace"),
        route: `/explorer/items/${mainWorkspace.id}`,
        icon: folderPersonalIcon.src,
      },
    ];

    if (sharedWorkspaces.children.length > 0) {
      nodes.push({
        id: "shared",
        label: t("explorer.tree.shared_space"),
        route: `/explorer/items/shared`,
        icon: sharedSpaceIcon.src,
      });
    }
    if (publicWorkspaces.children.length > 0) {
      nodes.push({
        id: "public",
        label: t("explorer.tree.public_space"),
        route: `/explorer/items/public`,
        icon: publicSpaceIcon.src,
      });
    }
    setNodes(nodes);
  }, [user, t]);

  useEffect(() => {
    initTree();
  }, [initTree, mobileNodesRefreshTrigger]);

  if (!nodes) {
    return null;
  }

  const renderNode = (node: ExplorerTreeMobileNode) => {
    const isSelected = router.asPath === node.route;

    return (
      <div
        id={`explorer__tree__mobile__node--${node.id}`}
        className={clsx(
          "explorer__tree__mobile__item",
          "explorer__tree__mobile__node",
          {
            "explorer__tree__mobile__node--selected": isSelected,
          }
        )}
        onClick={() => {
          router.push(node.route);
          setIsLeftPanelOpen(false);
        }}
      >
        <img src={node.icon} alt="" />
        <span>{node.label}</span>
      </div>
    );
  };

  return (
    <div className="explorer__tree__mobile">
      {nodes.map((node) => (
        <React.Fragment key={node.id}>{renderNode(node)}</React.Fragment>
      ))}
    </div>
  );
};
