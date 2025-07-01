import { Item, ItemType } from "@/features/drivers/types";
import {
  ExplorerGridBreadcrumbs,
  useBreadcrumbs,
} from "@/features/explorer/components/breadcrumbs/ExplorerGridBreadcrumbs";
import { useFirstLevelItems } from "@/features/explorer/hooks/useQueries";
import { getSdkPickerLayout } from "@/features/layouts/components/sdk/SdkLayout";
import { useRouter } from "next/router";
import clsx from "clsx";
import { ExplorerGridItems } from "@/features/explorer/components/grid/ExplorerGridItems";
import { useTranslation } from "react-i18next";

/**
 * Route used for SDK integration as popup ( File Picker ).
 */
export default function WorkspacesPage() {
  const router = useRouter();
  const { data: workspaces } = useFirstLevelItems();
  const { t } = useTranslation();
  const onNavigate = (item?: Item) => {
    if (item) {
      router.push(`/sdk/explorer/items/${item.id}`);
    } else {
      router.push(`/sdk/explorer/workspaces`);
    }
  };

  const breadcrumbs = useBreadcrumbs({
    handleNavigate: onNavigate,
  });

  return (
    <div>
      <ExplorerGridBreadcrumbs
        {...breadcrumbs}
        showSpacesItem={true}
        buildWithTreeContext={false}
      />
      <div
        className={clsx("explorer__grid ", {
          modal__move__empty: workspaces?.length === 0,
        })}
      >
        {workspaces && workspaces.length > 0 ? (
          <ExplorerGridItems
            isCompact
            items={workspaces}
            gridActionsCell={() => <div />}
            onNavigate={(e) => {
              const item = e.item as Item;
              breadcrumbs.update(item);
              onNavigate(item);
            }}
            canSelect={(item) => item.type === ItemType.FILE}
            disableItemDragAndDrop={true}
            displayMode="sdk"
            enableMetaKeySelection={true}
          />
        ) : (
          <div className="modal__move__empty">
            <span>{t("explorer.modal.move.empty_folder")}</span>
          </div>
        )}
      </div>
    </div>
  );
}

WorkspacesPage.getLayout = getSdkPickerLayout;
