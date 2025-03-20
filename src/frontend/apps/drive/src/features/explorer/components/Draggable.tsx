import { Item } from "@/features/drivers/types";
import { useDraggable } from "@dnd-kit/core";

type DraggableProps = {
  disabled?: boolean;
  item: Item;
  children: React.ReactNode;
  id: string;
  style?: React.CSSProperties;
  className?: string;
};
export const Draggable = (props: DraggableProps) => {
  const { attributes, listeners, setNodeRef } = useDraggable({
    id: props.id,
    disabled: props.disabled,
    data: {
      item: props.item,
    },
  });

  return (
    <div
      ref={setNodeRef}
      {...listeners}
      {...attributes}
      className={props.className}
      style={props.style}
    >
      {props.children}
    </div>
  );
};
