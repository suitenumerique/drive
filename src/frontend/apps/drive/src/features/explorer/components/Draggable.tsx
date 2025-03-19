import { useDraggable } from "@dnd-kit/core";

type DraggableProps = {
  disabled?: boolean;
  children: React.ReactNode;
  id: string;
};
export const Draggable = (props: DraggableProps) => {
  const { attributes, listeners, setNodeRef, transform } = useDraggable({
    id: props.id,
    disabled: props.disabled,
  });

  return (
    <div ref={setNodeRef} {...listeners} {...attributes}>
      {props.children}
    </div>
  );
};
