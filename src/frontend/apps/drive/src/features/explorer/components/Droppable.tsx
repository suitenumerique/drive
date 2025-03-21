import { Item } from "@/features/drivers/types";
import { useDroppable } from "@dnd-kit/core";
import {
  NodeRendererProps,
  TreeDataItem,
  TreeViewDataType,
} from "@gouvfr-lasuite/ui-kit";
import { useEffect } from "react";

type DroppableProps = {
  id: string;
  disabled?: boolean;
  item: Item;
  nodeTree?: NodeRendererProps<TreeDataItem<TreeViewDataType<Item>>>;
  children: React.ReactNode;
  onOver?: (isOver: boolean, fromItem: Item) => void;
};

export const Droppable = (props: DroppableProps) => {
  const { isOver, setNodeRef, active } = useDroppable({
    id: props.id,
    disabled: props.disabled,
    data: {
      item: props.item,
      nodeTree: props.nodeTree,
    },
  });
  const style = {};

  useEffect(() => {
    if (!props.disabled && props.onOver && active?.data.current?.item) {
      props.onOver(isOver, active?.data.current?.item as Item);
    }
  }, [isOver, props.item, active]);

  return (
    <div ref={setNodeRef} style={style} className="droppable">
      {props.children}
    </div>
  );
};
