import { Button } from "@gouvfr-lasuite/cunningham-react";
import { login } from "../Auth";
import { useTranslation } from "react-i18next";
import { SESSION_STORAGE_REDIRECT_AFTER_LOGIN_URL } from "@/features/api/fetchApi";

export const LoginButton = () => {
  const { t } = useTranslation();
  return (
    <Button
      className="drive__header__login-button"
      variant="tertiary"
      onClick={() => {
        sessionStorage.setItem(
          SESSION_STORAGE_REDIRECT_AFTER_LOGIN_URL,
          window.location.href
        );
        login();
      }}
    >
      {t("login")}
    </Button>
  );
};
