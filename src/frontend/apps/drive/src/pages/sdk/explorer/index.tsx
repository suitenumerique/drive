import { Item, ItemType, LinkReach } from "@/features/drivers/types";
import {
  EmbeddedExplorer,
  useEmbeddedExplorer,
} from "@/features/explorer/components/embedded-explorer/EmbeddedExplorer";
import {
  EmbeddedExplorerGridNameCell,
  EmbeddedExplorerGridNameCellProps,
} from "@/features/explorer/components/embedded-explorer/EmbeddedExplorerGridNameCell";
import {
  getSdkPickerLayout,
  useSdkContext,
} from "@/features/layouts/components/sdk/SdkLayout";
import { PickerFooter } from "@/features/sdk/SdkPickerFooter";
import { Tooltip } from "@openfun/cunningham-react";
import { useTranslation } from "react-i18next";

function canPickItem(item: Item) {
  if (item.type !== ItemType.FILE) {
    return false;
  }
  // Already set to public, so we can select it even if we can't update it.
  if (item.link_reach === LinkReach.PUBLIC) {
    return true;
  }
  // Means that anyway we can set the link_reach to public.
  if (item.abilities?.update) {
    return true;
  }
  return false;
}

export default function SdkExplorerPage() {
  const { token } = useSdkContext();

  const itemsExplorer = useEmbeddedExplorer({
    isCompact: true,
    gridProps: {
      enableMetaKeySelection: true,
      disableItemDragAndDrop: true,
      gridNameCell: SdkGridNameCell,
      gridActionsCell: () => <div />,
      displayMode: "sdk",
      canSelect: canPickItem,
    },
  });

  return (
    <div className="sdk__explorer__page">
      <div className="sdk__explorer">
        <EmbeddedExplorer {...itemsExplorer} />
      </div>
      <PickerFooter token={token} selectedItems={itemsExplorer.selectedItems} />
    </div>
  );
}

const SdkGridNameCell = (props: EmbeddedExplorerGridNameCellProps) => {
  const item = props.row.original;
  const { t } = useTranslation();

  if (item.type === ItemType.FOLDER || canPickItem(item)) {
    return <EmbeddedExplorerGridNameCell {...props} />;
  }
  return (
    <Tooltip content={t("sdk.explorer.cannot_pick")}>
      {/* Nested div is needed to make the tooltip work */}
      <div>
        <EmbeddedExplorerGridNameCell {...props}>
          <svg
            width="16"
            height="16"
            viewBox="0 0 16 16"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path
              d="M0.666504 13.9999L7.99984 1.33325L15.3332 13.9999H0.666504ZM2.9665 12.6666H13.0332L7.99984 3.99992L2.9665 12.6666ZM7.99984 11.9999C8.18873 11.9999 8.34706 11.936 8.47484 11.8083C8.60261 11.6805 8.6665 11.5221 8.6665 11.3333C8.6665 11.1444 8.60261 10.986 8.47484 10.8583C8.34706 10.7305 8.18873 10.6666 7.99984 10.6666C7.81095 10.6666 7.65261 10.7305 7.52484 10.8583C7.39706 10.986 7.33317 11.1444 7.33317 11.3333C7.33317 11.5221 7.39706 11.6805 7.52484 11.8083C7.65261 11.936 7.81095 11.9999 7.99984 11.9999ZM7.33317 9.99992H8.6665V6.66659H7.33317V9.99992Z"
              fill="#777777"
            />
          </svg>
        </EmbeddedExplorerGridNameCell>
      </div>
    </Tooltip>
  );
};

SdkExplorerPage.getLayout = getSdkPickerLayout;
