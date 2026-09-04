import { login } from "@/features/auth/Auth";
import { getSimpleLayout } from "@/features/layouts/components/simple/SimpleLayout";
import { GenericDisclaimer } from "@/features/ui/components/generic-disclaimer/GenericDisclaimer";
import { Button } from "@gouvfr-lasuite/ui-components";
import { useTranslation } from "react-i18next";

export default function UnauthorizedPage() {
  const { t } = useTranslation();
  return (
    <GenericDisclaimer
      message={t("401.title")}
      imageSrc="/assets/401-background.png"
    >
      <Button
        onClick={() => {
          // Redirect to the home page after login, to avoid loop redirection on /401
          const url = new URL("/", window.location.origin);
          login(url.toString());
        }}
      >
        {t("401.button")}
      </Button>
    </GenericDisclaimer>
  );
}

UnauthorizedPage.getLayout = getSimpleLayout;
