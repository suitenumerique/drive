import { getDriver } from "@/features/config/Config";
import { AppExplorer } from "@/features/explorer/components/app-view/AppExplorer";
import { ExplorerGridTrashActionsCell } from "@/features/explorer/components/trash/ExplorerGridTrashActionsCell";
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
} from "@gouvfr-lasuite/cunningham-react";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import undoIcon from "@/assets/icons/undo_blue.svg";
import cancelIcon from "@/assets/icons/cancel_blue.svg";
import { useGlobalExplorer } from "@/features/explorer/components/GlobalExplorerContext";
import { ItemFilters } from "@/features/drivers/Driver";
import { useState } from "react";
import { HardDeleteConfirmationModal } from "@/features/explorer/components/modals/HardDeleteConfirmationModal";
import { messageModalTrashNavigate } from "@/features/explorer/components/trash/utils";
import { setFromRoute } from "@/features/explorer/utils/utils";
import { DefaultRoute } from "@/utils/defaultRoutes";
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

  setFromRoute(DefaultRoute.TRASH);

  return (
    <AppExplorer
      childrenItems={trashItems}
      gridActionsCell={ExplorerGridTrashActionsCell}
      disableItemDragAndDrop={true}
      gridHeader={
        <div
          className="explorer__content__breadcrumbs"
          data-testid="trash-page-breadcrumbs"
        >
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
        messageModalTrashNavigate(modals);
      }}
    />
  );
}

TrashPage.getLayout = getGlobalExplorerLayout;

export const TrashPageSelectionBarActions = () => {
  const { selectedItems, setSelectedItems } = useGlobalExplorer();
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
        variant="tertiary"
        size="small"
        aria-label={t("explorer.grid.actions.restore")}
      />
      <Button
        onClick={() => hardDeleteConfirmationModal.open()}
        icon={<img src={cancelIcon.src} alt="" width={16} height={16} />}
        variant="tertiary"
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
