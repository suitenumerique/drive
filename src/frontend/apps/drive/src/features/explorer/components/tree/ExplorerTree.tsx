import { useMutation, useQueryClient } from "@tanstack/react-query";
import { getDriver } from "@/features/config/Config";
import {
  Button,
  Input,
  Modal,
  ModalProps,
  ModalSize,
  useModal,
} from "@openfun/cunningham-react";
import { useTranslation } from "react-i18next";
import { SubmitHandler, useForm } from "react-hook-form";
import {
  itemsToTreeItems,
  NavigationEventType,
  useExplorer,
} from "../ExplorerContext";
import { Item, ItemTreeItem } from "@/features/drivers/types";
import {
  HorizontalSeparator,
  TreeView,
  TreeViewDataType,
  TreeViewItem,
  TreeViewMoveResult,
  TreeViewNodeTypeEnum,
} from "@gouvfr-lasuite/ui-kit";
import { useEffect } from "react";
import { ExplorerTreeItem } from "./ExplorerTreeItem";
import { DroppableNodeTree } from "./DroppableNodeTree";
import { useMoveItems } from "../../api/useMoveItem";

type Inputs = {
  title: string;
};

export const ExplorerTree = () => {
  const { t } = useTranslation();
  const move = useMoveItems();

  const {
    tree: treeItem,
    firstLevelItems,
    itemId,
    treeObject,
    treeApiRef,
    onNavigate,
  } = useExplorer();

  useEffect(() => {
    if (!treeItem) {
      return;
    }
    const treeItems: Item[] = firstLevelItems ?? [];
    // Trouver l'élément treeItem dans treeItems et le remplacer
    const treeItemIndex = treeItems.findIndex(
      (item) => item.id === treeItem.id
    );
    if (treeItemIndex !== -1) {
      treeItems[treeItemIndex] = treeItem;
    } else {
      treeItems.unshift(treeItem);
    }

    const data: ItemTreeItem[] = itemsToTreeItems(treeItems);
    const items: TreeViewDataType<ItemTreeItem>[] = [];

    const firstNode: TreeViewDataType<ItemTreeItem> = {
      id: "PERSONAL_SPACE",
      nodeType: TreeViewNodeTypeEnum.TITLE,
      headerTitle: "Espace personnel",
    };

    items.push(firstNode);
    items.push(data[0]);

    if (data.length > 1) {
      const separator: TreeViewDataType<ItemTreeItem> = {
        id: "SEPARATOR",
        nodeType: TreeViewNodeTypeEnum.SEPARATOR,
      };

      const sharedSpace: TreeViewDataType<ItemTreeItem> = {
        id: "SHARED_SPACE",
        nodeType: TreeViewNodeTypeEnum.TITLE,
        headerTitle: "Espace partagé",
      };

      items.push(separator);
      items.push(sharedSpace);
      items.push(...data.slice(1));
    }

    treeObject.resetTree(items);
  }, [treeItem, firstLevelItems]);

  const createFolderModal = useModal();

  const handleMove = (result: TreeViewMoveResult) => {
    treeObject.handleMove(result);
    move.mutate({
      ids: [result.sourceId],
      parentId: result.targetModeId,
      oldParentId: result.oldParentId ?? itemId,
    });
  };

  return (
    <div>
      <div className="explorer__tree__actions">
        <div className="explorer__tree__actions__left">
          <Button
            icon={<span className="material-icons">add</span>}
            onClick={createFolderModal.open}
          >
            {t("explorer.tree.createFolder")}
          </Button>
          <Button color="secondary">{t("explorer.tree.import")}</Button>
        </div>
        <Button
          color="primary-text"
          aria-label={t("explorer.tree.search")}
          icon={<span className="material-icons">search</span>}
        ></Button>
      </div>
      <HorizontalSeparator withPadding={false} />
      <div>
        {/* {treeItem && drawTreeDuPauvre(treeItem)} */}
        <TreeView
          treeApiRef={treeApiRef}
          treeData={treeObject.nodes}
          handleMove={handleMove}
          canDrop={(args) => {
            return (
              args.index === 0 && args.parentNode?.willReceiveDrop === true
            );
          }}
          renderNode={(props) => {
            // console.log("renderNode", props);
            return (
              <DroppableNodeTree
                id={props.node.id}
                item={props.node.data.value}
                nodeTree={props}
              >
                <TreeViewItem
                  {...props}
                  loadChildren={(node) =>
                    treeObject.handleLoadChildren(node.id)
                  }
                  onClick={() => {
                    onNavigate({
                      type: NavigationEventType.ITEM,
                      item: props.node.data.value as Item,
                    });
                  }}
                >
                  <ExplorerTreeItem
                    item={props.node.data.value as ItemTreeItem}
                  />
                </TreeViewItem>
              </DroppableNodeTree>
            );
          }}
          rootNodeId={"root"}
        />
      </div>
      <ExplorerCreateFolderModal {...createFolderModal} />
    </div>
  );
};

/**
 * TODO: Create dedicated file.
 */
const ExplorerCreateFolderModal = (
  props: Pick<ModalProps, "isOpen" | "onClose">
) => {
  const { itemId } = useExplorer();
  const { t } = useTranslation();
  const driver = getDriver();
  const { register, handleSubmit } = useForm<Inputs>();

  const queryClient = useQueryClient();
  const createFolder = useMutation({
    mutationFn: (...payload: Parameters<typeof driver.createFolder>) => {
      return driver.createFolder(...payload);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["items", itemId],
      });
    },
  });

  const onSubmit: SubmitHandler<Inputs> = async (data) => {
    createFolder.mutate({
      ...data,
      parentId: itemId,
    });
    props.onClose();
  };

  return (
    <Modal
      {...props}
      size={ModalSize.SMALL}
      title={t("explorer.actions.createFolder.modal.title")}
      rightActions={
        <>
          <Button color="secondary" onClick={props.onClose}>
            {t("explorer.actions.createFolder.modal.cancel")}
          </Button>
          <Button type="submit" form="create-folder-form">
            {t("explorer.actions.createFolder.modal.submit")}
          </Button>
        </>
      }
    >
      <form
        onSubmit={handleSubmit(onSubmit)}
        id="create-folder-form"
        className="mt-s"
      >
        <Input
          label={t("explorer.actions.createFolder.modal.label")}
          fullWidth={true}
          {...register("title")}
        />
      </form>
    </Modal>
  );
};
