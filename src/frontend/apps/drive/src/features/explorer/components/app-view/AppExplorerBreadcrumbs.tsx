import { Button, useModal } from "@gouvfr-lasuite/cunningham-react";
import {
  NavigationEventType,
  useGlobalExplorer,
} from "@/features/explorer/components/GlobalExplorerContext";
import {
  HorizontalSeparator,
  IconSize,
  useDropdownMenu,
} from "@gouvfr-lasuite/ui-kit";
import { WorkspaceIcon } from "@/features/explorer/components/icons/ItemIcon";
import createFolderSvg from "@/assets/icons/add_folder.svg";
import { EmbeddedExplorerGridBreadcrumbs } from "@/features/explorer/components/embedded-explorer/EmbeddedExplorerGridBreadcrumbs";
import { ExplorerCreateFolderModal } from "../modals/ExplorerCreateFolderModal";
import { ImportDropdown } from "../item-actions/ImportDropdown";
import { useTranslation } from "react-i18next";
import { useRouter } from "next/router";
import { useBreadcrumbQuery } from "../../hooks/useBreadcrumb";
import { useMemo } from "react";
import {
  DefaultRoute,
  getDefaultRouteId,
  isDefaultRoute,
  ORDERED_DEFAULT_ROUTES,
} from "@/utils/defaultRoutes";

export const AppExplorerBreadcrumbs = () => {
  const { item, onNavigate } = useGlobalExplorer();
  const router = useRouter();
  const { t } = useTranslation();
  const createFolderModal = useModal();
  const importDropdown = useDropdownMenu();
  const onDefaultRoute = isDefaultRoute(router.pathname);
  const defaultRouteId = getDefaultRouteId(router.pathname);

  const showActions =
    (onDefaultRoute && defaultRouteId === DefaultRoute.MY_FILES) ||
    (!onDefaultRoute && item?.abilities.children_create);

  if (!item && !onDefaultRoute) {
    return null;
  }

  return (
    <>
      <div className="explorer__content__breadcrumbs">
        <EmbeddedExplorerGridBreadcrumbs
          currentItemId={item?.id}
          item={item}
          showMenuLastItem={true}
          onGoBack={(item) => {
            onNavigate({
              type: NavigationEventType.ITEM,
              item,
            });
          }}
        />

        {showActions && (
          <div className="explorer__content__breadcrumbs__actions">
            <ImportDropdown
              importMenu={importDropdown}
              trigger={
                <Button
                  variant="tertiary"
                  size="small"
                  onClick={() => {
                    importDropdown.setIsOpen(true);
                  }}
                >
                  {t("explorer.tree.import.label")}
                </Button>
              }
            />
            <Button
              icon={<img src={createFolderSvg.src} alt="Create Folder" />}
              variant="tertiary"
              data-testid="create-folder-button"
              size="small"
              onClick={() => {
                createFolderModal.open();
              }}
            />
          </div>
        )}
      </div>
      <div className="explorer__content__separator">
        <HorizontalSeparator withPadding={false} />
      </div>
      <ExplorerCreateFolderModal {...createFolderModal} parentId={item?.id} />
    </>
  );
};

export const ExplorerBreadcrumbsMobile = () => {
  const router = useRouter();
  const { t } = useTranslation();
  const { item, onNavigate } = useGlobalExplorer();
  const { data: breadcrumb } = useBreadcrumbQuery(item?.id);

  const defaultRouteId = getDefaultRouteId(router.pathname);
  const defaultRouteData = ORDERED_DEFAULT_ROUTES.find(
    (route) => route.id === defaultRouteId
  );

  const items = useMemo(() => {
    if (!breadcrumb) {
      return null;
    }
    const workspace = breadcrumb[0];
    const current = breadcrumb[breadcrumb.length - 1];
    const parent = breadcrumb[breadcrumb.length - 2] ?? workspace;
    return {
      workspace,
      current,
      parent,
    };
  }, [breadcrumb]);

  if (!item && defaultRouteData) {
    return (
      <div className="explorer__content__breadcrumbs--mobile">
        <div className="explorer__content__breadcrumbs--mobile__default-route">
          <defaultRouteData.icon size={IconSize.MEDIUM} />

          {t(defaultRouteData.label)}
        </div>
      </div>
    );
  }

  if (!items) {
    return null;
  }

  const { workspace, parent, current } = items;

  const workspaceTitle = workspace.main_workspace
    ? t("explorer.workspaces.mainWorkspace")
    : workspace.title;
  const isRoot = current.id === workspace.id;
  return (
    <div className="explorer__content__breadcrumbs--mobile">
      {isRoot ? (
        <div className="explorer__content__breadcrumbs--mobile__workspace">
          <WorkspaceIcon
            isMainWorkspace={workspace.main_workspace}
            iconSize={IconSize.X_SMALL}
          />
          <span>{workspaceTitle}</span>
        </div>
      ) : (
        <div className="explorer__content__breadcrumbs--mobile__container">
          <div className="explorer__content__breadcrumbs--mobile__container__actions">
            <Button
              variant="bordered"
              color="neutral"
              icon={<span className="material-icons">chevron_left</span>}
              onClick={() => {
                if (parent?.id === DefaultRoute.SHARED_WITH_ME) {
                  router.push("/explorer/items/shared-with-me");
                } else if (parent?.id === DefaultRoute.MY_FILES) {
                  router.push("/explorer/items/my-files");
                } else if (parent?.id === DefaultRoute.FAVORITES) {
                  router.push("/explorer/items/favorites");
                } else if (parent?.id === DefaultRoute.RECENT) {
                  router.push("/explorer/items/recent");
                } else {
                  onNavigate({
                    type: NavigationEventType.ITEM,
                    item: parent,
                  });
                }
              }}
            />
          </div>
          <div className="explorer__content__breadcrumbs--mobile__container__info">
            <div className="explorer__content__breadcrumbs--mobile__container__info__title">
              <WorkspaceIcon
                isMainWorkspace={workspace.main_workspace}
                iconSize={IconSize.X_SMALL}
              />
              <span>{workspaceTitle}</span>
            </div>
            <div className="explorer__content__breadcrumbs--mobile__container__info__folder">
              {current.title}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
