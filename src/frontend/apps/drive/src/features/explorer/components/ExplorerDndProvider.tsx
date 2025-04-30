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
import { addItemsMovedToast } from "./toasts/addItemsMovedToast";
import { useModal } from "@openfun/cunningham-react";
import { createContext, useContext, useState } from "react";
import {
  ConfirmationMoveState,
  ExplorerTreeMoveConfirmationModal,
} from "./tree/ExplorerTreeMoveConfirmationModal";

const activationConstraint = {
  distance: 20,
};

type ExplorerDndProviderProps = {
  children: React.ReactNode;
};

type DndContextType = {
  overedItemIds: Record<string, boolean>;
  setOveredItemIds: React.Dispatch<
    React.SetStateAction<Record<string, boolean>>
  >;
};

const DragItemContext = createContext<DndContextType | undefined>(undefined);

export const useDragItemContext = () => {
  const context = useContext(DragItemContext);
  if (!context) {
    throw new Error("useDndContext must be used within an ExplorerDndProvider");
  }
  return context;
};

export const ExplorerDndProvider = ({ children }: ExplorerDndProviderProps) => {
  const moveConfirmationModal = useModal();
  const [overedItemIds, setOveredItemIds] = useState<Record<string, boolean>>(
    {}
  );
  const [moveState, setMoveState] = useState<ConfirmationMoveState | undefined>(
    undefined
  );
  const { itemId, selectedItems, setSelectedItems } = useExplorer();

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

    setSelectedItems([item]);
  };

  const handleMoveConfirmation = async (newParentId: string) => {
    selectedItems
      .map((item) => item.id)
      .forEach((id) => {
        treeContext?.treeData.moveNode(id, newParentId, 0);
      });

    setOveredItemIds({});
    const ids = selectedItems.map((item) => item.id);
    await moveItems.mutateAsync(
      {
        ids: ids,
        parentId: newParentId,
        oldParentId: itemId,
      },
      {
        onSuccess: () => {
          addItemsMovedToast(ids.length);
        },
      }
    );
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

    const pathActiveItemSegments = activeItem.path.split(".");
    const pathOverItemSegments = overItem.path.split(".");

    if (pathActiveItemSegments[0] !== pathOverItemSegments[0]) {
      setMoveState({
        sourceItem: activeItem,
        targetItem: overItem,
      });
      moveConfirmationModal.open();
      return;
    }

    await handleMoveConfirmation(overItem.id);
  };

  return (
    <>
      <DndContext
        sensors={sensors}
        modifiers={[snapToTopLeft]}
        onDragStart={handleDragStart}
        onDragEnd={handleDragEnd}
      >
        <DragOverlay dropAnimation={null}>
          <ExplorerDragOverlay count={selectedItems.length} />
        </DragOverlay>
        <DragItemContext.Provider
          value={{
            overedItemIds,
            setOveredItemIds,
          }}
        >
          {children}
        </DragItemContext.Provider>
      </DndContext>
      {moveState && moveConfirmationModal.isOpen && (
        <ExplorerTreeMoveConfirmationModal
          itemsCount={selectedItems.length}
          isOpen={moveConfirmationModal.isOpen}
          onClose={() => {
            moveConfirmationModal.close();
            setMoveState(undefined);
          }}
          sourceItem={moveState.sourceItem}
          targetItem={moveState.targetItem}
          onMove={() => {
            handleMoveConfirmation(moveState.targetItem.id);
            moveConfirmationModal.close();
          }}
        />
      )}
    </>
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

  const canDrop = overItem.abilities.children_create;
  const canMove = activeItem.abilities.move;

  if (!canDrop || !canMove) {
    return false;
  }

  if (!activePath || !overPath) {
    return false;
  }

  const activePathSegments = activePath.split(".");
  const overPathSegments = overPath.split(".");

  // Cannot drop an item into its children
  if (overPath.startsWith(activePath)) {
    return false;
  }

  if (activePathSegments.length === 1 && overPathSegments.length === 1) {
    return activePathSegments[0] === overPathSegments[0];
  }

  if (activePathSegments.length < 2) {
    return false;
  }

  if (overPathSegments.length < 1) {
    return false;
  }

  // Check if the active item is a direct child of the over item
  // by removing the last segment from active path and comparing with over path
  const activePathWithoutLastSegment = activePathSegments
    .slice(0, -1)
    .join(".");

  // Cannot drop an item into its direct parent
  if (activePathWithoutLastSegment === overPath) {
    return false;
  }

  return true;
};
