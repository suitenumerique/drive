import { RecentIcon } from "@/features/ui/components/icon/RecentIcon";
import { MyFilesIcon } from "@/features/ui/components/icon/MyFilesIcon";
import { SharedWithMeIcon } from "@/features/ui/components/icon/SharedWithMeIcon";
import { StarredIcon } from "@/features/ui/components/icon/StarredIcon";
import { TrashIcon } from "@/features/ui/components/icon/TrashIcon";
import { JSX } from "react";
import { IconProps } from "@gouvfr-lasuite/ui-kit";

export enum DefaultRoute {
  MY_FILES = "my-files",
  RECENT = "recent",
  SHARED_WITH_ME = "shared-with-me",
  FAVORITES = "favorites",
  TRASH = "trash",
}
export type DefaultRouteData = {
  id: DefaultRoute;
  label: string;
  route: string;
  icon: (props: Partial<IconProps>) => JSX.Element;
};
export const ORDERED_DEFAULT_ROUTES: DefaultRouteData[] = [
  {
    id: DefaultRoute.RECENT,
    label: "explorer.tree.recent",
    route: "/explorer/items/recent",
    icon: RecentIcon,
  },
  {
    id: DefaultRoute.MY_FILES,
    label: "explorer.tree.my_files",
    route: "/explorer/items/my-files",
    icon: MyFilesIcon,
  },
  {
    id: DefaultRoute.SHARED_WITH_ME,
    label: "explorer.tree.shared_with_me",
    route: "/explorer/items/shared-with-me",
    icon: SharedWithMeIcon,
  },
  {
    id: DefaultRoute.FAVORITES,
    label: "explorer.tree.favorites",
    route: "/explorer/items/favorites",
    icon: StarredIcon,
  },
];

export const TRASH_ROUTE_DATA: DefaultRouteData = {
  id: DefaultRoute.TRASH,
  label: "explorer.tree.trash",
  route: "/explorer/trash",
  icon: TrashIcon,
};

export const getDefaultRoute = (
  pathname: string,
): DefaultRouteData | undefined => {
  if (pathname === TRASH_ROUTE_DATA.route) {
    return TRASH_ROUTE_DATA;
  }
  return ORDERED_DEFAULT_ROUTES.find((r) => r.route === pathname);
};

export const getDefaultRouteId = (
  pathname: string,
): DefaultRoute | undefined => {
  return getDefaultRoute(pathname)?.id;
};

export const isDefaultRoute = (pathname: string): boolean => {
  return getDefaultRoute(pathname) !== undefined;
};

export const isMyFilesRoute = (pathname: string): boolean => {
  return getDefaultRouteId(pathname) === DefaultRoute.MY_FILES;
};

export const getMyFilesQueryKey = (): string[] => {
  return ["items", "infinite", JSON.stringify({ is_creator_me: true })];
};

export const getRecentItemsQueryKey = (): string[] => {
  return ["items", "infinite"];
};

export const getSharedWithMeQueryKey = (): string[] => {
  return ["items", "infinite", JSON.stringify({ is_creator_me: false })];
};

export const getQueryKeyForRouteId = (pathname: string): string[] => {
  const route = getDefaultRouteId(pathname);
  switch (route) {
    case DefaultRoute.MY_FILES:
      return getMyFilesQueryKey();
    case DefaultRoute.RECENT:
      return getRecentItemsQueryKey();
    case DefaultRoute.SHARED_WITH_ME:
      return getSharedWithMeQueryKey();

    default:
      return [];
  }
};
