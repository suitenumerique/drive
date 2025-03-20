import { ItemTreeItem } from "@/features/drivers/types";
import { useDndContext, useDroppable } from "@dnd-kit/core";
import {
  NodeRendererProps,
  TreeDataItem,
  TreeViewDataType,
  TreeViewNodeTypeEnum,
} from "@gouvfr-lasuite/ui-kit";
import clsx from "clsx";
import { useEffect, useRef } from "react";
import { useExplorer } from "../ExplorerContext";
import { canDrop } from "../ExplorerDndProvider";

type DroppableNodeTreeProps = {
  id: string;
  disabled?: boolean;
  item: TreeViewDataType<ItemTreeItem>;
  nodeTree?: NodeRendererProps<TreeDataItem<TreeViewDataType<ItemTreeItem>>>;
  children: React.ReactNode;
};

export const DroppableNodeTree = (props: DroppableNodeTreeProps) => {
  const { treeObject } = useExplorer();
  const { active } = useDndContext();
  const canDropItem = active
    ? canDrop(active?.data?.current?.item, props.item as ItemTreeItem)
    : false;

  const { isOver, setNodeRef } = useDroppable({
    id: props.id,
    disabled:
      props.disabled || props.item.nodeType !== TreeViewNodeTypeEnum.NODE,
    data: {
      item: props.item,
      nodeTree: props.nodeTree,
    },
  });

  const timeoutRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    if (!props.nodeTree) {
      return;
    }
    if (isOver) {
      // Si isOver devient true, on met en place un timeout
      timeoutRef.current = setTimeout(async () => {
        const node = props.nodeTree?.node.data.value;
        if (
          node?.children?.length === 0 &&
          node?.childrenCount &&
          node.childrenCount > 0
        ) {
          await treeObject.handleLoadChildren(node.id);
        }
        props.nodeTree?.node.open();
      }, 800);
    } else {
      // Si isOver devient false, on annule le timeout et on réinitialise l'état
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
        timeoutRef.current = null;
      }
    }

    // Nettoyage au démontage du composant
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, [isOver]);

  if (props.item.nodeType !== TreeViewNodeTypeEnum.NODE) {
    return props.children;
  }

  return (
    <div
      ref={setNodeRef}
      className={clsx("explorer__tree__item__droppable", {
        over: isOver && canDropItem,
      })}
    >
      {props.children}
    </div>
  );
};
