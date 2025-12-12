export enum DefaultRoute {
  MY_FILES = "my_files",
  RECENT = "recent",
  SHARED_WITH_ME = "shared-with-me",
  FAVORITES = "favorites",
}
export type DefaultRouteData = {
  id: DefaultRoute;
  label: string;
  route: string;
  iconName: string;
};
export const ORDERED_DEFAULT_ROUTES: DefaultRouteData[] = [
  {
    id: DefaultRoute.RECENT,
    label: "explorer.tree.recent",
    route: "/explorer/items/recent",
    iconName: "access_time",
  },
  {
    id: DefaultRoute.MY_FILES,
    label: "explorer.tree.my_files",
    route: "/explorer/items/my_files",
    iconName: "person_outline",
  },
  {
    id: DefaultRoute.SHARED_WITH_ME,
    label: "explorer.tree.shared_with_me",
    route: "/explorer/items/shared-with-me",
    iconName: "people_alt",
  },
  {
    id: DefaultRoute.FAVORITES,
    label: "explorer.tree.favorites",
    route: "/explorer/items/favorites",
    iconName: "star_border",
  },
];

export const getDefaultRoute = (
  pathname: string
): DefaultRouteData | undefined => {
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
