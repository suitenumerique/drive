import {
  ExplorerGridItemsExplorer,
  useExplorerGridItemsExplorer,
} from "@/features/explorer/components/grid/ExplorerGridItemsExplorer";
import { getSdkPickerLayout } from "@/features/layouts/components/sdk/SdkLayout";
import { useTranslation } from "react-i18next";

export default function SdkExplorerPage() {
  const { t } = useTranslation();

  const itemsExplorer = useExplorerGridItemsExplorer({
    isCompact: true,
    gridProps: {
      enableMetaKeySelection: false,
      disableItemDragAndDrop: true,
      gridActionsCell: () => <div />,
      displayMode: "sdk",
    },
    emptyContent: () => <span>{t("explorer.modal.move.empty_folder")}</span>,
  });

  return <ExplorerGridItemsExplorer {...itemsExplorer} />;
}

SdkExplorerPage.getLayout = getSdkPickerLayout;
