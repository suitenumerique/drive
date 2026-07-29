import { GenericDisclaimer } from "@/features/ui/components/generic-disclaimer/GenericDisclaimer";
import { SpinnerPage } from "@/features/ui/components/spinner/SpinnerPage";
import {
  CustomFilesPreview,
  CustomFilesPreviewMode,
} from "@/features/ui/preview/CustomFilesPreview";
import { Icon } from "@gouvfr-lasuite/ui-kit";
import { Button } from "@gouvfr-lasuite/cunningham-react";
import { useRouter } from "next/router";
import { useTranslation } from "react-i18next";
import { useItem } from "@/features/explorer/hooks/useQueries";
import { GlobalLayout } from "@/features/layouts/components/global/GlobalLayout";
import { useConfig } from "@/features/config/ConfigProvider";
import { useEffect } from "react";

export default function FilePage() {
  const { t } = useTranslation();
  const router = useRouter();
  const itemId = router.query.id as string;
  const { config } = useConfig();

  const { data: item, isLoading, error } = useItem(itemId);

  // Items pointing to an external app are not previewable here: hand the
  // user over to the owning application.
  const externalAppUrl =
    item?.metadata?.external_app === "docs" && config?.FRONTEND_DOCS_URL
      ? `${config.FRONTEND_DOCS_URL}/docs/${item.id}/`
      : null;

  useEffect(() => {
    if (externalAppUrl) {
      window.location.replace(externalAppUrl);
    }
  }, [externalAppUrl]);

  // On 403, 401, the user is automatically redirected to the 401/403 page.

  // If the error is a 401 or 403, we want to show the spinner page because an auto redirect is happening.
  if (
    isLoading ||
    externalAppUrl ||
    (error && [401, 403].includes(error.code))
  ) {
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
      <CustomFilesPreview
        currentItem={item}
        items={[item]}
        mode={CustomFilesPreviewMode.CONTEXTUAL}
      />
    </div>
  );
}

FilePage.getLayout = function getLayout(page: React.ReactElement) {
  return <GlobalLayout>{page}</GlobalLayout>;
};
