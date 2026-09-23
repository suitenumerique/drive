import { useEffect, useRef, useState } from "react";
import { getDriver } from "@/features/config/Config";
import { RestrictedDescendantsDeleteModal } from "../components/modals/RestrictedDescendantsDeleteModal";
import {
  addToast,
  ToasterItem,
} from "@/features/ui/components/toaster/Toaster";
import { useMutationDeleteItems } from "./useMutations";
import { useTranslation } from "react-i18next";
import { useTreeUtils } from "./useTreeUtils";
import { useGlobalExplorer } from "../components/GlobalExplorerContext";

export const useDeleteItem = () => {
  const { t } = useTranslation();
  const treeUtils = useTreeUtils();
  const deleteItemsMutation = useMutationDeleteItems();
  const { cancelUploadsForDeletedItems } = useGlobalExplorer();

  const busy = useRef(false);
  const mounted = useRef(true);
  const decision = useRef<((confirmed: boolean) => void) | null>(null);
  const [isPending, setIsPending] = useState(false);
  const [confirmationCount, setConfirmationCount] = useState<number | null>(
    null,
  );

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
      decision.current?.(false);
    };
  }, []);

  const onDecide = (confirmed: boolean) => {
    decision.current?.(confirmed);
    decision.current = null;
    setConfirmationCount(null);
  };

  const deleteItems = async (ids: string[]): Promise<boolean> => {
    if (busy.current || ids.length === 0) return false;
    const itemIds = [...new Set(ids)];
    busy.current = true;
    setIsPending(true);
    try {
      const metadata = await getDriver().getItemsDeletionInfo(itemIds);
      if (!mounted.current) return false;
      if (
        itemIds.some(
          (id) => typeof metadata?.[id]?.hasRestrictedDescendent !== "boolean",
        )
      ) {
        throw new Error("Incomplete deletion metadata");
      }
      if (itemIds.some((id) => metadata[id].hasRestrictedDescendent)) {
        const confirmed = await new Promise<boolean>((resolve) => {
          decision.current = resolve;
          setConfirmationCount(itemIds.length);
        });
        if (!confirmed || !mounted.current) return false;
      }

      await deleteItemsMutation.mutateAsync(itemIds);
      cancelUploadsForDeletedItems(itemIds);
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
      return true;
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
      return false;
    } finally {
      busy.current = false;
      if (mounted.current) setIsPending(false);
    }
  };

  return {
    deleteItems,
    isPending,
    isModalOpen: confirmationCount !== null,
    modals:
      confirmationCount !== null ? (
        <RestrictedDescendantsDeleteModal
          count={confirmationCount}
          onDecide={onDecide}
        />
      ) : null,
  };
};
