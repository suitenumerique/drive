import recentIcon from "@/assets/icons/defaultTabs/sidebar/recents.svg";
import myFilesIcon from "@/assets/icons/defaultTabs/sidebar/my_files.svg";
import sharedWithMeIcon from "@/assets/icons/defaultTabs/sidebar/shared_with_me.svg";
import starredIcon from "@/assets/icons/defaultTabs/sidebar/starred.svg";
import trashIcon from "@/assets/icons/defaultTabs/sidebar/trash.svg";

import recentBreadcrumbIcon from "@/assets/icons/defaultTabs/breadcrumbs/recents.svg";
import myFilesBreadcrumbIcon from "@/assets/icons/defaultTabs/breadcrumbs/my_files.svg";
import sharedWithMeBreadcrumbIcon from "@/assets/icons/defaultTabs/breadcrumbs/shared_with_me.svg";
import starredBreadcrumbIcon from "@/assets/icons/defaultTabs/breadcrumbs/starred.svg";
import trashBreadcrumbIcon from "@/assets/icons/defaultTabs/breadcrumbs/trash.svg";

export enum DefaultRoute {
  MY_FILES = "my_files",
  RECENT = "recent",
  SHARED_WITH_ME = "shared-with-me",
  FAVORITES = "favorites",
  TRASH = "trash",
}
export type DefaultRouteData = {
  id: DefaultRoute;
  label: string;
  route: string;
  iconName: string;
  iconSrc: string;
  breadcrumbIconSrc: string;
};
export const ORDERED_DEFAULT_ROUTES: DefaultRouteData[] = [
  {
    id: DefaultRoute.RECENT,
    label: "explorer.tree.recent",
    route: "/explorer/items/recent",
    iconName: "access_time",
    iconSrc: recentIcon.src,
    breadcrumbIconSrc: recentBreadcrumbIcon.src,
  },
  {
    id: DefaultRoute.MY_FILES,
    label: "explorer.tree.my_files",
    route: "/explorer/items/my_files",
    iconName: "person_outline",
    iconSrc: myFilesIcon.src,
    breadcrumbIconSrc: myFilesBreadcrumbIcon.src,
  },
  {
    id: DefaultRoute.SHARED_WITH_ME,
    label: "explorer.tree.shared_with_me",
    route: "/explorer/items/shared-with-me",
    iconName: "group",
    iconSrc: sharedWithMeIcon.src,
    breadcrumbIconSrc: sharedWithMeBreadcrumbIcon.src,
  },
  {
    id: DefaultRoute.FAVORITES,
    label: "explorer.tree.favorites",
    route: "/explorer/items/favorites",
    iconName: "star_border",
    iconSrc: starredIcon.src,
    breadcrumbIconSrc: starredBreadcrumbIcon.src,
  },
];

export const TRASH_ROUTE_DATA: DefaultRouteData = {
  id: DefaultRoute.TRASH,
  label: "explorer.tree.trash",
  route: "/explorer/trash",
  iconName: "delete",
  iconSrc: trashIcon.src,
  breadcrumbIconSrc: trashBreadcrumbIcon.src,
};

export const getDefaultRoute = (
  pathname: string
): DefaultRouteData | undefined => {
  if (pathname === TRASH_ROUTE_DATA.route) {
    return TRASH_ROUTE_DATA;
  }
  return ORDERED_DEFAULT_ROUTES.find((r) => r.route === pathname);
};

export const getDefaultRouteId = (
  pathname: string
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
