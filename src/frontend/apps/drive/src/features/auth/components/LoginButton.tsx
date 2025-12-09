import { Button } from "@openfun/cunningham-react";
import { useTranslation } from "react-i18next";
import { SESSION_STORAGE_REDIRECT_AFTER_LOGIN_URL } from "@/features/api/fetchApi";
import { useAuth } from "../Auth";

export const LoginButton = () => {
  const { t } = useTranslation();
  const { login } = useAuth();

  return (
    <Button
      className="drive__header__login-button"
      variant="tertiary"
      onClick={() => {
        sessionStorage.setItem(
          SESSION_STORAGE_REDIRECT_AFTER_LOGIN_URL,
          window.location.href
        );
        login?.();
      }}
    >
      {t("login")}
    </Button>
  );
};
