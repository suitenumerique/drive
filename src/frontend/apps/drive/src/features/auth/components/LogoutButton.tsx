import { Button } from "@openfun/cunningham-react";
import { useTranslation } from "react-i18next";
import { useAuth } from "../Auth";

export const LogoutButton = () => {
  const { t } = useTranslation();
  const { logout } = useAuth();

  return (
    <Button variant="tertiary" onClick={logout} fullWidth={true}>
      {t("logout")}
    </Button>
  );
};
