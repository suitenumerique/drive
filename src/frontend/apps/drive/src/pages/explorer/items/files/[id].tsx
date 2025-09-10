import { APIError } from "@/features/api/APIError";
import { getDriver } from "@/features/config/Config";
import { Item } from "@/features/drivers/types";
import { itemToPreviewFile } from "@/features/explorer/utils/utils";
import { ItemInfo } from "@/features/items/components/ItemInfo";
import { useDownloadItem } from "@/features/items/hooks/useDownloadItem";
import { GenericDisclaimer } from "@/features/ui/components/generic-disclaimer/GenericDisclaimer";
import { SpinnerPage } from "@/features/ui/components/spinner/SpinnerPage";
import { FilePreview } from "@/features/ui/preview/files-preview/FilesPreview";
import { Icon } from "@gouvfr-lasuite/ui-kit";
import { Button } from "@openfun/cunningham-react";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/router";
import { useTranslation } from "react-i18next";

export default function FilePage() {
  const { t } = useTranslation();
  const router = useRouter();
  const itemId = router.query.id as string;
  const { handleDownloadItem } = useDownloadItem();
  // On 403, 401, the user is automatically redirected to the 401/403 page.
  const {
    data: item,
    isLoading,
    error,
  } = useQuery<Item, APIError>({
    queryKey: ["items", itemId],
    queryFn: async () => {
      return getDriver().getItem(itemId);
    },
  });
  // If the error is a 401 or 403, we want to show the spinner page because an auto redirect is happening.
  if (isLoading || (error && [401, 403].includes(error.code))) {
    return <SpinnerPage />;
  }

  // Can happen if the file is deleted.
  if (!item) {
    return (
      <GenericDisclaimer
        message={t("explorer.files.not_found.description")}
        imageSrc="/assets/403-background.png"
      >
        <Button href="/" icon={<Icon name="home" />}>
          {t("403.button")}
        </Button>
      </GenericDisclaimer>
    );
  }

  return (
    <div>
      <FilePreview
        isOpen={true}
        hideCloseButton={true}
        hideNav={true}
        title={t("file_preview.title")}
        files={[itemToPreviewFile(item)]}
        onChangeFile={() => void 0}
        handleDownloadFile={() => handleDownloadItem(item)}
        openedFileId={item.id}
        sidebarContent={item && <ItemInfo item={item} />}
      />
    </div>
  );
}
