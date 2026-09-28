import { GenericDisclaimer } from "@/features/ui/components/generic-disclaimer/GenericDisclaimer";
import { SpinnerPage } from "@/features/ui/components/spinner/SpinnerPage";
import {
  CustomFilesPreview,
  CustomFilesPreviewMode,
} from "@/features/ui/preview/CustomFilesPreview";
import { Icon, Button } from "@gouvfr-lasuite/ui-components";
import { useRouter } from "next/router";
import { useTranslation } from "react-i18next";
import { useItem } from "@/features/explorer/hooks/useQueries";
import { GlobalLayout } from "@/features/layouts/components/global/GlobalLayout";
import { useAutoAcceptPendingMembers } from "@/features/encryption/sharing/useAutoAcceptPendingMembers";
import type { NextPageWithLayout } from "@/pages/_app";

const FilePage: NextPageWithLayout = () => {
  const { t } = useTranslation();
  const router = useRouter();
  const itemId = router.query.id as string;

  const { data: item, isLoading, error } = useItem(itemId);
  // This page has no explorer context, which is what hands the key to pending
  // members when a manager opens an encrypted item: do it here too.
  useAutoAcceptPendingMembers(item);

  // On 403, 401, the user is automatically redirected to the 401/403 page.

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
      <CustomFilesPreview
        currentItem={item}
        items={[item]}
        mode={CustomFilesPreviewMode.CONTEXTUAL}
      />
    </div>
  );
};

// GlobalLayout carries the auth and vault providers the encrypted viewers need.
FilePage.getLayout = function getLayout(page: React.ReactElement) {
  return <GlobalLayout>{page}</GlobalLayout>;
};

export default FilePage;
