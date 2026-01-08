import { getSimpleLayout } from "@/features/layouts/components/simple/SimpleLayout";
import { GenericDisclaimer } from "@/features/ui/components/generic-disclaimer/GenericDisclaimer";
import { Icon } from "@gouvfr-lasuite/ui-kit";
import { Button } from "@gouvfr-lasuite/cunningham-react";
import { useTranslation } from "react-i18next";

export default function UnauthorizedPage() {
  const { t } = useTranslation();
  return (
    <GenericDisclaimer
      message={t("403.title")}
      imageSrc="/assets/403-background.png"
    >
      <Button href="/" icon={<Icon name="home" />}>
        {t("403.button")}
      </Button>
    </GenericDisclaimer>
  );
}

UnauthorizedPage.getLayout = getSimpleLayout;
