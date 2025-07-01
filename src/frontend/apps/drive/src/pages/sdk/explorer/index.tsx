import { ItemType } from "@/features/drivers/types";
import {
  ExplorerGridItemsExplorer,
  useExplorerGridItemsExplorer,
} from "@/features/explorer/components/grid/ExplorerGridItemsExplorer";
import {
  getSdkPickerLayout,
  useSdkContext,
} from "@/features/layouts/components/sdk/SdkLayout";
import { PickerFooter } from "@/features/sdk/SdkPickerFooter";

export default function SdkExplorerPage() {
  const { token } = useSdkContext();

  const itemsExplorer = useExplorerGridItemsExplorer({
    isCompact: true,
    gridProps: {
      enableMetaKeySelection: true,
      disableItemDragAndDrop: true,
      gridActionsCell: () => <div />,
      displayMode: "sdk",
      canSelect: (item) => item.type === ItemType.FILE,
    },
  });

  return (
    <div className="sdk__explorer__page">
      <div className="sdk__explorer">
        <ExplorerGridItemsExplorer {...itemsExplorer} />
      </div>
      <PickerFooter token={token} selectedItems={itemsExplorer.selectedItems} />
    </div>
  );
}

SdkExplorerPage.getLayout = getSdkPickerLayout;
