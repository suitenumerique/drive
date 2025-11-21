import { LanguagePicker } from "../header/Header";
import { LogoutButton } from "@/features/auth/components/LogoutButton";
import { useAuth } from "@/features/auth/Auth";
import { LoginButton } from "@/features/auth/components/LoginButton";
import { useConfig } from "@/features/config/ConfigProvider";

export const LeftPanelMobile = () => {
  const { user } = useAuth();
  const { config } = useConfig();

  return (
    <div className="drive__home__left-panel">
      {!config?.FRONTEND_HIDE_LANGUAGE_PICKER && <LanguagePicker />}
      {!config?.FRONTEND_HIDE_AUTH_BUTTONS && (user ? <LogoutButton /> : <LoginButton />)}
    </div>
  );
};
