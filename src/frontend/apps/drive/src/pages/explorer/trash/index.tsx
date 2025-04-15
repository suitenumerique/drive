import { getDriver } from "@/features/config/Config";
import { Explorer } from "@/features/explorer/components/Explorer";
import { ExplorerGridTrashActionsCell } from "@/features/explorer/components/grid/ExplorerGridTrashActionsCell";
import { useMutationRestoreItems } from "@/features/explorer/hooks/useMutations";
import { getGlobalExplorerLayout } from "@/features/layouts/components/explorer/ExplorerLayout";
import { addToast } from "@/features/ui/components/toaster/Toaster";
import { ToasterItem } from "@/features/ui/components/toaster/Toaster";
import { Button } from "@openfun/cunningham-react";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import undoIcon from "@/assets/icons/undo_blue.svg";
import { useExplorer } from "@/features/explorer/components/ExplorerContext";
export default function TrashPage() {
  const { t } = useTranslation();
  const { data: trashItems } = useQuery({
    queryKey: ["items", "trash"],
    queryFn: () => getDriver().getTrashItems(),
  });

  return (
    <Explorer
      childrenItems={trashItems}
      gridActionsCell={ExplorerGridTrashActionsCell}
      disableItemDragAndDrop={true}
      gridHeader={
        <div className="explorer__content__breadcrumbs">
          <div className="explorer__content__header__title">
            {t("explorer.trash.title")}
          </div>
          <div className="explorer__content__header__description">
            {t("explorer.trash.description")}
          </div>
        </div>
      }
      selectionBarActions={<TrashPageSelectionBarActions />}
    />
  );
}

TrashPage.getLayout = getGlobalExplorerLayout;

export const TrashPageSelectionBarActions = () => {
  const { selectedItems, setSelectedItems } = useExplorer();
  const restoreItem = useMutationRestoreItems();
  const { t } = useTranslation();

  const handleRestore = async () => {
    addToast(
      <ToasterItem>
        <span className="material-icons">delete</span>
        <span>
          {t("explorer.actions.restore.toast", { count: selectedItems.length })}
        </span>
      </ToasterItem>
    );
    await restoreItem.mutateAsync(selectedItems.map((item) => item.id));
    setSelectedItems([]);
  };

  return (
    <>
      {/* <Button
        onClick={handleClearSelection}
        icon={<span className="material-icons">download</span>}
        color="primary-text"
        size="small"
        aria-label={t("explorer.selectionBar.download")}
      /> */}
      {/* <Button
        onClick={handleClearSelection}
        icon={<span className="material-icons">arrow_forward</span>}
        color="primary-text"
        size="small"
        aria-label={t("explorer.selectionBar.move")}
      /> */}
      <Button
        onClick={handleRestore}
        icon={<img src={undoIcon.src} alt="" width={16} height={16} />}
        color="primary-text"
        size="small"
        aria-label={t("explorer.grid.actions.restore")}
      />
    </>
  );
};
