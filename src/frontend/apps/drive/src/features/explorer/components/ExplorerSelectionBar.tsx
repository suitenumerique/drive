import { Button } from "@openfun/cunningham-react";
import { useTranslation } from "react-i18next";
import { useExplorer } from "./ExplorerContext";
import { getDriver } from "@/features/config/Config";
import { useQueryClient } from "@tanstack/react-query";
import { useMutation } from "@tanstack/react-query";
import { addToast } from "@/features/ui/components/toaster/Toaster";
import { ToasterItem } from "@/features/ui/components/toaster/Toaster";
import { Item } from "@/features/drivers/types";

export const ExplorerSelectionBar = () => {
  const { t } = useTranslation();
  const { selectedItems, setSelectedItemIds, item } = useExplorer();
  const driver = getDriver();

  const handleClearSelection = () => {
    setSelectedItemIds({});
  };

  const queryClient = useQueryClient();
  const deleteItems = useMutation({
    mutationFn: async (...payload: Parameters<typeof driver.deleteItems>) => {
      await driver.deleteItems(...payload);
    },
    onMutate: async (itemIds) => {
      // Cancel any outgoing refetches
      await queryClient.cancelQueries({
        queryKey: ["items", item!.id, "children"],
      });

      // Snapshot the previous value
      const previousItems = queryClient.getQueryData([
        "items",
        item!.id,
        "children",
      ]);

      // Optimistically update to the new value
      queryClient.setQueryData(["items", item!.id, "children"], (old: Item[]) =>
        old ? old.filter((i: Item) => !itemIds.includes(i.id)) : old
      );

      // Return a context object with the snapshotted value
      return { previousItems };
    },
    onError: (err, variables, context) => {
      // If the mutation fails, use the context returned from onMutate to roll back
      queryClient.setQueryData(
        ["items", item!.id, "children"],
        context?.previousItems
      );
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["items", item!.id],
      });
    },
  });

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
