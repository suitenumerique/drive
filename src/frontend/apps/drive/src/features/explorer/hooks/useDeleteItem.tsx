import {
  addToast,
  ToasterItem,
} from "@/features/ui/components/toaster/Toaster";
import { useMutationDeleteItems } from "./useMutations";
import { useTranslation } from "react-i18next";
import { useTreeUtils } from "./useTreeUtils";

export const useDeleteItem = () => {
  const { t } = useTranslation();
  const treeUtils = useTreeUtils();
  const deleteItemsMutation = useMutationDeleteItems();

  const deleteItems = async (itemIds: string[]) => {
    try {
      await deleteItemsMutation.mutateAsync(itemIds);
      for (const itemId of itemIds) {
        treeUtils.deleteAllByOriginalId(itemId);
      }
      addToast(
        <ToasterItem>
          <span className="material-icons">delete</span>
          <span>
            {t("explorer.actions.delete.toast", { count: itemIds.length })}
          </span>
        </ToasterItem>,
      );
    } catch {
      addToast(
        <ToasterItem type="error">
          <span className="material-icons">delete</span>
          <span>
            {t("explorer.actions.delete.toast_error", {
              count: itemIds.length,
            })}
          </span>
        </ToasterItem>,
      );
    }
  };

  return { deleteItems: deleteItems };
};
