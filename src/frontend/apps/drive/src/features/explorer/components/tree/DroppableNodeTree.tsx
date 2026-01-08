import { TreeItem, TreeItemData } from "@/features/drivers/types";
import { useDndContext, useDroppable } from "@dnd-kit/core";
import {
  NodeRendererProps,
  TreeDataItem,
  TreeViewNodeTypeEnum,
  useTreeContext,
} from "@gouvfr-lasuite/ui-kit";
import clsx from "clsx";
import { useEffect, useRef } from "react";
import { canDrop } from "../ExplorerDndProvider";
import { DefaultRoute } from "@/utils/defaultRoutes";

type DroppableNodeTreeProps = {
  id: string;
  disabled?: boolean;
  item: TreeItem;
  nodeTree?: NodeRendererProps<TreeDataItem<TreeItemData>>;
  children: React.ReactNode;
};

export const DroppableNodeTree = (props: DroppableNodeTreeProps) => {
  const treeContext = useTreeContext();
  const { active } = useDndContext();
  const isDropDisabled =
    props.item.nodeType !== TreeViewNodeTypeEnum.NODE &&
    props.item.id !== DefaultRoute.FAVORITES;

  const canDropItem = active
    ? canDrop(active?.data?.current?.item, props.item as TreeItem)
    : false;

  const { isOver, setNodeRef } = useDroppable({
    id: props.id,
    disabled: props.disabled || isDropDisabled,
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
      timeoutRef.current = setTimeout(async () => {
        const node = props.nodeTree?.node.data.value;

        const children = node?.children ?? [];
        if (
          children.length === 0 &&
          node?.childrenCount &&
          node.childrenCount > 0
        ) {
          await treeContext?.treeData.handleLoadChildren(node.id);
        }
        props.nodeTree?.node.open();
      }, 800);
    } else {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
        timeoutRef.current = null;
      }
    }

    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, [isOver]);

  if (isDropDisabled) {
    return (
      <div className="explorer__tree__item__droppable">{props.children}</div>
    );
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
