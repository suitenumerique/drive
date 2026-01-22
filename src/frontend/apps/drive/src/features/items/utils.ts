import { getDefaultRouteId, DefaultRoute } from "@/utils/defaultRoutes";
import { useRouter } from "next/router";
import { Item } from "../drivers/types";

export const downloadFile = async (url: string, title: string) => {
  const a = document.createElement("a");
  a.style.display = "none";
  a.href = url;
  a.download = title;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
};

export const canCreateChildren = (item: Item, pathname: string) => {
  const isMyFiles = getDefaultRouteId(pathname) === DefaultRoute.MY_FILES;
  return item?.abilities?.children_create || isMyFiles;
};

export const useCanCreateChildren = (item: Item) => {
  const router = useRouter();
  return canCreateChildren(item, router.pathname);
};
