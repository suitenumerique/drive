import { getDriver } from "@/features/config/Config";
import { ItemType } from "@/features/drivers/types";
import { Explorer } from "@/features/explorer/components/Explorer";
import { useFirstLevelItems } from "@/features/explorer/hooks/useQueries";
import { getSdkPickerLayout } from "@/features/layouts/components/sdk/SdkLayout";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/router";

/**
 * Route used for SDK integration as popup ( File Picker ).
 */
export default function WorkspacesPage() {
  const { data: firstLevelItems } = useFirstLevelItems();

  return (
    <Explorer
      childrenItems={firstLevelItems}
      canSelect={(item) => item.type === ItemType.FILE}
      disableAreaSelection={true}
      disableItemDragAndDrop={true}
    />
  );
}

WorkspacesPage.getLayout = getSdkPickerLayout;
