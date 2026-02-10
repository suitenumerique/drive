import { useTranslation } from "react-i18next";
import { useDndContext } from "@dnd-kit/core";
import { Item } from "@/features/drivers/types";
import clsx from "clsx";

type ExplorerDragOverlayProps = {
  count: number;
};

export const ExplorerDragOverlay = ({ count }: ExplorerDragOverlayProps) => {
  const { t } = useTranslation();
  const dndContext = useDndContext();
  const filesCount = count > 0 ? count : 1;
  const activeItem = dndContext?.active?.data?.current?.item as Item;
  const canMove = activeItem?.abilities?.move;

  return (
    <div
      className={clsx("explorer__drag-overlay", {
        "explorer__drag-overlay__cannot-move": !canMove,
      })}
    >
      {!canMove
        ? t(
            `explorer.drag_overlay.cannot_move_${activeItem?.type === "folder" ? "folder" : "file"}`,
          )
        : t("explorer.drag_overlay.files_selected", { count: filesCount })}
    </div>
  );
};
