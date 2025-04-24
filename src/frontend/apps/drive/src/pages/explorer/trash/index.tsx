import { getDriver } from "@/features/config/Config";
import { Explorer } from "@/features/explorer/components/Explorer";
import { ExplorerGridTrashActionsCell } from "@/features/explorer/components/grid/ExplorerGridTrashActionsCell";
import {
  useMutationHardDeleteItems,
  useMutationRestoreItems,
} from "@/features/explorer/hooks/useMutations";
import { getGlobalExplorerLayout } from "@/features/layouts/components/explorer/ExplorerLayout";
import { addToast } from "@/features/ui/components/toaster/Toaster";
import { ToasterItem } from "@/features/ui/components/toaster/Toaster";
import {
  Button,
  Decision,
  useModal,
  useModals,
} from "@openfun/cunningham-react";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import undoIcon from "@/assets/icons/undo_blue.svg";
import cancelIcon from "@/assets/icons/cancel_blue.svg";
import { useExplorer } from "@/features/explorer/components/ExplorerContext";
import { ItemFilters } from "@/features/drivers/Driver";
import { useState } from "react";
import { HardDeleteConfirmationModal } from "@/features/explorer/components/modals/HardDeleteConfirmationModal";
export default function TrashPage() {
  const { t } = useTranslation();
  const [filters, setFilters] = useState<ItemFilters>({});
  const { data: trashItems } = useQuery({
    queryKey: [
      "items",
      "trash",
      ...(Object.keys(filters).length ? [JSON.stringify(filters)] : []),
    ],
    queryFn: () => getDriver().getTrashItems(filters),
  });

  const modals = useModals();

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
      filters={filters}
      onFiltersChange={setFilters}
      onNavigate={() => {
        modals.messageModal({
          title: t("explorer.trash.navigate.modal.title"),
          children: (
            <div className="clr-greyscale-600">
              {t("explorer.trash.navigate.modal.description")}
            </div>
          ),
        });
      }}
    />
  );
}

TrashPage.getLayout = getGlobalExplorerLayout;

export const TrashPageSelectionBarActions = () => {
  const { selectedItems, setSelectedItems } = useExplorer();
  const restoreItem = useMutationRestoreItems();
  const hardDeleteConfirmationModal = useModal();
  const hardDeleteItem = useMutationHardDeleteItems();
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

  const handleHardDelete = async (decision: Decision) => {
    if (!decision) {
      return;
    }
    addToast(
      <ToasterItem>
        <span className="material-icons">delete</span>
        <span>{t("explorer.actions.hard_delete.toast", { count: 1 })}</span>
      </ToasterItem>
    );
    await hardDeleteItem.mutateAsync(selectedItems.map((item) => item.id));
    setSelectedItems([]);
  };

  return (
    <>
      <Button
        onClick={handleRestore}
        icon={<img src={undoIcon.src} alt="" width={16} height={16} />}
        color="primary-text"
        size="small"
        aria-label={t("explorer.grid.actions.restore")}
      />
      <Button
        onClick={() => hardDeleteConfirmationModal.open()}
        icon={<img src={cancelIcon.src} alt="" width={16} height={16} />}
        color="primary-text"
        size="small"
        aria-label={t("explorer.grid.actions.hard_delete")}
      />
      {hardDeleteConfirmationModal.isOpen && (
        <HardDeleteConfirmationModal
          {...hardDeleteConfirmationModal}
          onDecide={handleHardDelete}
          multiple={selectedItems.length > 1}
        />
      )}
    </>
  );
};
