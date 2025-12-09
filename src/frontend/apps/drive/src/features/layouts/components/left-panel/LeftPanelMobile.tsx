import { Gaufre } from "@/features/ui/components/gaufre/Gaufre";
import { UserProfile } from "@/features/ui/components/user/UserProfile";
import { useResponsive } from "@gouvfr-lasuite/ui-kit";

export const LeftPanelMobile = () => {
  const { isTablet } = useResponsive();

  if (!isTablet) {
    return null;
  }

  return (
    <div className="drive__home__left-panel">
      <div className="drive__home__left-panel__gaufre">
        <Gaufre />
        <UserProfile />
      </div>
    </div>
  );
};
