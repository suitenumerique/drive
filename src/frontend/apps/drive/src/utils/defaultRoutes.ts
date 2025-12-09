export enum DefaultRoute {
  MY_FILES = "my_files",
  RECENT = "recent",
  SHARED_WITH_ME = "shared-with-me",
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
