import { LanguagePicker } from "../header/Header";
import { LogoutButton } from "@/features/auth/components/LogoutButton";
import { useAuth } from "@/features/auth/Auth";
import { LoginButton } from "@/features/auth/components/LoginButton";
import { useThemeCustomizationElementsDisplay } from "@/hooks/useThemeCustomization";

export const LeftPanelMobile = () => {
  const { user } = useAuth();
  const authButtonsCustomization = useThemeCustomizationElementsDisplay('auth_buttons');
  const languagePickerCustomization = useThemeCustomizationElementsDisplay('language_picker');

  return (
    <div className="drive__home__left-panel">
      {languagePickerCustomization.show && <LanguagePicker />}
      {authButtonsCustomization.show && (user ? <LogoutButton /> : <LoginButton />)}
    </div>
  );
};
