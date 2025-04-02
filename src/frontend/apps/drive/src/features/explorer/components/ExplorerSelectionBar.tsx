import { Button } from "@openfun/cunningham-react";
import { useTranslation } from "react-i18next";
import { useExplorer } from "./ExplorerContext";
import { addToast } from "@/features/ui/components/toaster/Toaster";
import { ToasterItem } from "@/features/ui/components/toaster/Toaster";
import { useMutationDeleteItems } from "../hooks/useMutations";
import { useEffect } from "react";

export const ExplorerSelectionBar = () => {
  const { t } = useTranslation();
  const { selectedItems, setSelectedItemIds, setRightPanelForcedItem } =
    useExplorer();

  const handleClearSelection = () => {
    setSelectedItemIds({});
    setRightPanelForcedItem(undefined);
  };

  const deleteItems = useMutationDeleteItems();

  const handleDelete = async () => {
    addToast(
      <ToasterItem>
        <span className="material-icons">delete</span>
        <span>
          {t("explorer.actions.delete.toast", { count: selectedItems.length })}
        </span>
      </ToasterItem>
    );
    await deleteItems.mutateAsync(selectedItems.map((item) => item.id));
    setSelectedItemIds({});
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedItems]);

  return (
    <div className="explorer__selection-bar">
      <div className="explorer__selection-bar__left">
        <div className="explorer__selection-bar__caption">
          {t("explorer.selectionBar.caption", {
            count: selectedItems.length,
          })}
        </div>
        <div className="explorer__selection-bar__actions">
          <Button
            onClick={handleClearSelection}
            icon={<span className="material-icons">download</span>}
            color="primary-text"
            size="small"
            aria-label={t("explorer.selectionBar.download")}
          />
          <Button
            onClick={handleClearSelection}
            icon={<span className="material-icons">arrow_forward</span>}
            color="primary-text"
            size="small"
            aria-label={t("explorer.selectionBar.move")}
          />
          <Button
            onClick={handleDelete}
            icon={<span className="material-icons">delete</span>}
            color="primary-text"
            size="small"
            aria-label={t("explorer.selectionBar.delete")}
          />
        </div>
      </div>
      <div className="explorer__selection-bar__actions">
        <Button
          onClick={handleClearSelection}
          icon={<span className="material-icons">close</span>}
          color="primary-text"
          size="small"
          aria-label={t("explorer.selectionBar.reset_selection")}
        />
      </div>
    </div>
  );
};
