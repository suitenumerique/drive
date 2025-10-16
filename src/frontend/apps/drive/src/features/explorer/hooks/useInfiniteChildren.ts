import { getDriver } from "@/features/config/Config";
import { ItemFilters } from "@/features/drivers/Driver";
import { Item } from "@/features/drivers/types";
import { useInfiniteScroll } from "@/features/ui/components/infinite-scroll";

export const useInfiniteChildren = (itemId: string, filters?: ItemFilters) => {
  return useInfiniteScroll<Item>({
    queryKey: ["children", itemId, filters || {}],
    queryFn: ({ pageParam = 1 }) => {
      console.log("pageParam", pageParam);
      const params = {
        page: pageParam.toString(),
        page_size: "20", // Use the same page size as the backend default
        ...(filters ? filters : {}),
      };
      const driver = getDriver();
      return driver.getChildren(itemId, params);
    },
    enabled: !!itemId,
    pageSize: 20,
  });
};
