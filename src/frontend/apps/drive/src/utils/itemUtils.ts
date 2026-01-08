import { Item } from "@/features/drivers/types";
import { DefaultRoute, getDefaultRouteId } from "./defaultRoutes";
import { useRouter } from "next/router";

export const canCreateChildren = (item: Item, pathname: string) => {
  const isMyFiles = getDefaultRouteId(pathname) === DefaultRoute.MY_FILES;
  return item?.abilities?.children_create || isMyFiles;
};

export const useCanCreateChildren = (item: Item) => {
  const router = useRouter();
  return canCreateChildren(item, router.pathname);
};
