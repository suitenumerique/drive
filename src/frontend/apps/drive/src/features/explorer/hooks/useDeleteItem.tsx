import {
  addToast,
  ToasterItem,
} from "@/features/ui/components/toaster/Toaster";
import { useMutationDeleteItems } from "./useMutations";
import { useTranslation } from "react-i18next";

export const useDeleteItem = () => {
  const { t } = useTranslation();
  const deleteItemsMutation = useMutationDeleteItems();
  const deleteItems = async (itemIds: string[]) => {
    try {
      await deleteItemsMutation.mutateAsync(itemIds);
      addToast(
        <ToasterItem>
          <span className="material-icons">delete</span>
          <span>
            {t("explorer.actions.delete.toast", { count: itemIds.length })}
          </span>
        </ToasterItem>
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
        </ToasterItem>
      );
    }
  };

  return { deleteItems: deleteItems };
};
