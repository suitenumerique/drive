import { Button, useModal } from "@gouvfr-lasuite/cunningham-react";
import { useTranslation } from "react-i18next";
import { useGlobalExplorer } from "@/features/explorer/components/GlobalExplorerContext";
import { useAppExplorer } from "@/features/explorer/components/app-view/AppExplorer";
import { addToast } from "@/features/ui/components/toaster/Toaster";
import { ToasterItem } from "@/features/ui/components/toaster/Toaster";
import { useMutationDeleteItems } from "@/features/explorer/hooks/useMutations";
import { useEffect } from "react";
import { ExplorerMoveFolder } from "@/features/explorer/components/modals/move/ExplorerMoveFolderModal";

export const ExplorerSelectionBar = () => {
  const { t } = useTranslation();
  const { selectedItems, setSelectedItems, setRightPanelForcedItem } =
    useGlobalExplorer();
  const { selectionBarActions } = useAppExplorer();

  const handleClearSelection = () => {
    setSelectedItems([]);
    setRightPanelForcedItem(undefined);
  };

  return (
    <div className="explorer__selection-bar">
      <div className="explorer__selection-bar__left">
        <div className="explorer__selection-bar__caption">
          {t("explorer.selectionBar.caption", {
            count: selectedItems.length,
          })}
        </div>
        <div className="explorer__selection-bar__actions">
          {selectionBarActions ? (
            selectionBarActions
          ) : (
            <ExplorerSelectionBarActions />
          )}
        </div>
      </div>
      <div className="explorer__selection-bar__actions">
        <Button
          onClick={handleClearSelection}
          icon={<span className="material-icons">close</span>}
          variant="tertiary"
          size="small"
          aria-label={t("explorer.selectionBar.reset_selection")}
        />
      </div>
    </div>
  );
};

export const ExplorerSelectionBarActions = () => {
  const { t } = useTranslation();
  const { selectedItems, setSelectedItems, item } = useGlobalExplorer();
  const moveModal = useModal();

  const deleteItems = useMutationDeleteItems();

  const handleDelete = async () => {
    let canDelete = true;
    for (const item of selectedItems) {
      if (!item.abilities?.destroy) {
        canDelete = false;
      }
    }
    if (canDelete) {
      addToast(
        <ToasterItem>
          <span className="material-icons">delete</span>
          <span>
            {t("explorer.actions.delete.toast", {
              count: selectedItems.length,
            })}
          </span>
        </ToasterItem>
      );
      setSelectedItems([]);
      await deleteItems.mutateAsync(selectedItems.map((item) => item.id));
    } else {
      addToast(
        <ToasterItem type="error">
          <span className="material-icons">delete</span>
          <span>{t("explorer.actions.delete.low_rights_toast")}</span>
        </ToasterItem>
      );
    }
  };

  // Add event listener when component mounts and remove when unmounts
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key === "Backspace") {
        event.preventDefault();
        handleDelete();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [selectedItems]);

  return (
    <>
      {/* <Button
        onClick={handleClearSelection}
        icon={<span className="material-icons">download</span>}
        variant="tertiary"
        size="small"
        aria-label={t("explorer.selectionBar.download")}
      /> */}
      <Button
        onClick={handleDelete}
        icon={<span className="material-icons">delete</span>}
        variant="tertiary"
        size="small"
        aria-label={t("explorer.selectionBar.delete")}
      />
      <Button
        onClick={moveModal.open}
        icon={<span className="material-icons">arrow_forward</span>}
        variant="tertiary"
        size="small"
        aria-label={t("explorer.selectionBar.move")}
      />

      {moveModal.isOpen && (
        <ExplorerMoveFolder
          {...moveModal}
          itemsToMove={selectedItems}
          initialFolderId={item?.id}
        />
      )}
    </>
  );
};
