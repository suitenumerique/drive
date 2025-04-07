import {
  DndContext,
  DragEndEvent,
  DragOverlay,
  DragStartEvent,
  KeyboardSensor,
  Modifier,
  MouseSensor,
  TouchSensor,
  useSensor,
  useSensors,
} from "@dnd-kit/core";
import { getEventCoordinates } from "@dnd-kit/utilities";
import { useMoveItems } from "../api/useMoveItem";
import { useExplorer } from "./ExplorerContext";
import { Item, TreeItem } from "@/features/drivers/types";
import { ExplorerDragOverlay } from "./tree/ExploreDragOverlay";
import { TreeViewNodeTypeEnum, useTreeContext } from "@gouvfr-lasuite/ui-kit";

const activationConstraint = {
  distance: 20,
};

type ExplorerDndProviderProps = {
  children: React.ReactNode;
};

export const ExplorerDndProvider = ({ children }: ExplorerDndProviderProps) => {
  const {
    setSelectedItemIds: setSelectedItems,
    itemId,
    selectedItems,
  } = useExplorer();

  const treeContext = useTreeContext<TreeItem>();

  const moveItems = useMoveItems();
  const mouseSensor = useSensor(MouseSensor, {
    activationConstraint,
  });

  const touchSensor = useSensor(TouchSensor, {
    activationConstraint,
  });
  const keyboardSensor = useSensor(KeyboardSensor, {});

  const sensors = useSensors(mouseSensor, touchSensor, keyboardSensor);

  const handleDragStart = (ev: DragStartEvent) => {
    document.body.style.cursor = "grabbing";
    const item = ev.active.data.current?.item as Item;
    if (!item) {
      return;
    }

    if (selectedItems.length > 0) {
      return;
    }

    setSelectedItems({
      [item.id]: true,
    });
  };

  const handleDragEnd = async ({ active, over }: DragEndEvent) => {
    document.body.style.cursor = "default";

    const activeItem = active.data.current?.item as Item;
    const overItem = over?.data.current?.item as Item;

    if (!activeItem || !overItem) {
      return;
    }
    if (activeItem.id === overItem.id) {
      return;
    }

    const canDropResult = canDrop(activeItem, overItem);

    if (!canDropResult) {
      return;
    }

    selectedItems
      .map((item) => item.id)
      .forEach((id) => {
        treeContext?.treeData.moveNode(id, overItem.id, 0);
      });

    await moveItems.mutateAsync({
      ids: selectedItems.map((item) => item.id),
      parentId: overItem.id,
      oldParentId: itemId,
    });
  };

  return (
    <DndContext
      sensors={sensors}
      modifiers={[snapToTopLeft]}
      onDragStart={handleDragStart}
      onDragEnd={handleDragEnd}
    >
      <DragOverlay dropAnimation={null}>
        <ExplorerDragOverlay count={selectedItems.length} />
      </DragOverlay>
      {children}
    </DndContext>
  );
};

export const snapToTopLeft: Modifier = ({
  activatorEvent,
  draggingNodeRect,
  transform,
}) => {
  if (draggingNodeRect && activatorEvent) {
    const activatorCoordinates = getEventCoordinates(activatorEvent);

    if (!activatorCoordinates) {
      return transform;
    }

    const offsetX = activatorCoordinates.x - draggingNodeRect.left;
    const offsetY = activatorCoordinates.y - draggingNodeRect.top;

    return {
      ...transform,
      x: transform.x + offsetX - 5,
      y: transform.y + offsetY - 5,
    };
  }

  return transform;
};

export const canDrop = (activeItem: Item, overItem: Item | TreeItem) => {
  if (activeItem.id === overItem.id) {
    return false;
  }

  if ("nodeType" in overItem) {
    if (overItem.nodeType !== TreeViewNodeTypeEnum.NODE) {
      return false;
    }
  }

  const activePath = activeItem.path;
  const overPath = overItem.path;

  if (!activePath || !overPath) {
    return false;
  }

  const activePathSegments = activePath.split(".");
  const overPathSegments = overPath.split(".");

  if (activePathSegments.length === 1 && overPathSegments.length === 1) {
    return activePathSegments[0] === overPathSegments[0];
  }

  if (activePathSegments.length < 2) {
    return false;
  }

  if (overPathSegments.length < 1) {
    return false;
  }

  const result =
    activePathSegments[activePathSegments.length - 2] !==
    overPathSegments[overPathSegments.length - 1];

  return result;
};
