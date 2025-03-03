import { Header as KitHeader } from "@lasuite/ui-kit";
import { Button } from "@openfun/cunningham-react";
import logo from "@/assets/logo.svg";
import { useAuth, logout } from "@/features/auth/Auth";

export const Header = () => {
  return (
    <KitHeader
      leftIcon={<img src={logo.src} alt="logo" />}
      rightIcon={<HeaderRight />}
    />
  );
};

export const HeaderRight = () => {
  const { user } = useAuth();
  return (
    <div>
      {user && (
        <Button onClick={logout} color="primary-text">
          Logout
        </Button>
      )}
    </div>
  );
};
