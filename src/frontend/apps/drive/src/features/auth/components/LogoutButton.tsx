import { Button } from "@gouvfr-lasuite/ui-components";
import { logout } from "../Auth";
import { useTranslation } from "react-i18next";

export const LogoutButton = () => {
  const { t } = useTranslation();
  return (
    <Button variant="tertiary" onClick={logout} fullWidth={true}>
      {t("logout")}
    </Button>
  );
};
