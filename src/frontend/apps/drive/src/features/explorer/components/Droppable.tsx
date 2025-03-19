import { Item } from "@/features/drivers/types";
import { useDroppable } from "@dnd-kit/core";
import { useEffect } from "react";

type DroppableProps = {
  id: string;
  disabled?: boolean;
  item: Item;
  children: React.ReactNode;
  onOver?: (isOver: boolean, item: Item) => void;
};

export const Droppable = (props: DroppableProps) => {
  const { isOver, setNodeRef } = useDroppable({
    id: props.id,
    disabled: props.disabled,
    data: {
      item: props.item,
    },
  });
  const style = {};

  useEffect(() => {
    if (!props.disabled && props.onOver) {
      props.onOver(isOver, props.item);
    }
  }, [isOver, props.item]);

  return (
    <div ref={setNodeRef} style={style}>
      {props.children}
    </div>
  );
};
