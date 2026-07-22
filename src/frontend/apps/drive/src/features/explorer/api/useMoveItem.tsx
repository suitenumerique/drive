import { getDriver } from "@/features/config/Config";
import { getCanUploadErrorDescription } from "@/utils/entitlements";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import {
  addToast,
  ToasterItem,
} from "@/features/ui/components/toaster/Toaster";
import { useRemoveItemsFromPaginatedList } from "../hooks/useOptimisticPagination";
import { useRefreshEntitlementsQueryCache } from "../hooks/useRefreshItems";
import {
  getMyFilesQueryKey,
  getRecentItemsQueryKey,
  getSharedWithMeQueryKey,
} from "@/utils/defaultRoutes";

export const useMoveItems = () => {
  type MoveItemPayload = {
    ids: string[];
    parentId?: string;
    oldParentId?: string;
  };

  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const driver = getDriver();

  const removeItems = useRemoveItemsFromPaginatedList();
  const refreshEntitlements = useRefreshEntitlementsQueryCache();

  return useMutation({
    mutationFn: async (payload: MoveItemPayload) => {
      await driver.moveItems(payload.ids, payload.parentId);
    },
    onMutate: async (payload: MoveItemPayload) => {
      // Cancel any outgoing refetches to avoid overwriting optimistic updates
      await queryClient.cancelQueries({
        queryKey: ["items", payload.oldParentId, "children"],
      });

      await queryClient.cancelQueries({
        queryKey: ["items", payload.parentId, "children"],
      });
    },
    onSuccess: (data, payload: MoveItemPayload) => {
      removeItems(["items", payload.oldParentId], payload.ids);
      removeItems(getMyFilesQueryKey(), payload.ids);
      removeItems(getSharedWithMeQueryKey(), payload.ids);
      removeItems(getRecentItemsQueryKey(), payload.ids);
      queryClient.invalidateQueries({
        queryKey: ["items", payload.parentId],
      });
      refreshEntitlements();
    },
    onError: (err, variables) => {
      // If the mutation fails, you could invalidate to ensure fresh data
      queryClient.invalidateQueries({
        queryKey: ["items", variables.oldParentId, "children", "infinite"],
      });

      queryClient.invalidateQueries({
        queryKey: ["items", variables.parentId, "children", "infinite"],
      });

      addToast(
        <ToasterItem type="error">
          <span className="material-icons">arrow_forward</span>
          <span>
            {getCanUploadErrorDescription(err, (key) =>
              t(`explorer.modal.move.errors.${key}`),
            ) ??
              t("explorer.actions.move.toast_error", {
                count: variables.ids.length,
              })}
          </span>
        </ToasterItem>,
      );
    },
    meta: {
      // The onError above already toasts a localized message.
      noGlobalError: true,
    },
  });
};
