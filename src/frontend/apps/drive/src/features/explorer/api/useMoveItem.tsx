import { getDriver } from "@/features/config/Config";
import { Item } from "@/features/drivers/types";
import { PaginatedChildrenResult } from "@gouvfr-lasuite/ui-kit";
import { useMutation, useQueryClient } from "@tanstack/react-query";

export const useMoveItems = () => {
  type MoveItemPayload = {
    ids: string[];
    parentId: string;
    oldParentId: string;
  };

  const queryClient = useQueryClient();
  const driver = getDriver();
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
      const queriesData = queryClient.getQueriesData({
        queryKey: ["items", payload.oldParentId, "children", "infinite"],
      });

      queriesData.forEach((query) => {
        const key = query[0];
        const data: { pages: PaginatedChildrenResult<Item>[] } = JSON.parse(
          JSON.stringify(query[1])
        ) as {
          pages: PaginatedChildrenResult<Item>[];
        };

        data.pages.forEach((page) => {
          page.children = page.children?.filter(
            (child) => !payload.ids.includes(child.id)
          );
        });

        queryClient.setQueryData(key, data);
      });
    },
    onError: (err, variables) => {
      // If the mutation fails, you could invalidate to ensure fresh data
      queryClient.invalidateQueries({
        queryKey: ["items", variables.oldParentId, "children", "infinite"],
      });

      queryClient.invalidateQueries({
        queryKey: ["items", variables.parentId, "children", "infinite"],
      });
    },
  });
};
