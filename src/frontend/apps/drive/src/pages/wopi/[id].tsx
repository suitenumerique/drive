import { useEffect } from "react";
import { useRouter } from "next/router";
import { useTranslation } from "react-i18next";
import { Icon } from "@gouvfr-lasuite/ui-kit";
import { Button } from "@gouvfr-lasuite/cunningham-react";

import { GenericDisclaimer } from "@/features/ui/components/generic-disclaimer/GenericDisclaimer";
import { SpinnerPage } from "@/features/ui/components/spinner/SpinnerPage";
import { useItem } from "@/features/explorer/hooks/useQueries";
import { useRefreshItemCache } from "@/features/explorer/hooks/useRefreshItems";
import { itemToPreviewFile } from "@/features/explorer/utils/utils";
import { WopiEditorFrame } from "@/features/ui/preview/viewers/wopi/WopiEditorFrame";
import { FilePreviewType } from "@/features/ui/preview/FilesPreview";

export default function WopiPage() {
  const { t } = useTranslation();
  const router = useRouter();
  const itemId = router.query.id as string;

  const { data: item, isLoading, error } = useItem(itemId);
  const refreshItemCache = useRefreshItemCache();

  useEffect(() => {
    if (!item) return;
    const previousTitle = document.title;
    document.title = `${item.title} - ${t("app_title")}`;
    return () => {
      document.title = previousTitle;
    };
  }, [item, t]);

  if (isLoading || (error && [401, 403].includes(error.code))) {
    return <SpinnerPage />;
  }

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

  const handleRename = (file: FilePreviewType, newName: string) => {
    refreshItemCache(file.id, { title: newName });
  };

  return (
    <div className="wopi-page">
      <WopiEditorFrame
        item={itemToPreviewFile(item)}
        onFileRename={handleRename}
      />
    </div>
  );
}
