import { LanguagePicker } from "../header/Header";
import { LogoutButton } from "@/features/auth/components/LogoutButton";
import { useAuth } from "@/features/auth/Auth";
import { LoginButton } from "@/features/auth/components/LoginButton";

export const LeftPanelMobile = () => {
  const { user } = useAuth();
  return (
    <div className="drive__home__left-panel">
      <LanguagePicker />
      {user ? <LogoutButton /> : <LoginButton />}
    </div>
  );
};
