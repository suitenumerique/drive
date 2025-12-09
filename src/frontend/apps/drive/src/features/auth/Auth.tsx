import React, { PropsWithChildren, useEffect, useState } from "react";

import { User } from "@/features/auth/types";
import { posthog } from "posthog-js";
import { SpinnerPage } from "@/features/ui/components/spinner/SpinnerPage";
import { getDriver } from "../config/Config";

interface AuthContextInterface {
  user?: User | null;
  init?: () => Promise<User | null>;
  refreshUser?: () => Promise<void>;
  login?: (returnTo?: string) => void;
  logout?: () => void;
}

export const AuthContext = React.createContext<AuthContextInterface>({});

export const useAuth = () => React.useContext(AuthContext);

export const Auth = ({
  children,
}: PropsWithChildren) => {
  const driver = getDriver();
  const [user, setUser] = useState<User | null>();

  const init = async () => {
    try {
      const data = await driver.getConnectedUser();
      setUser(data);
      return data;
    } catch {
      setUser(null);
      return null;
    }
  };

  const refreshUser = async () => {
    void init();
  };

  const login = (returnTo?: string) => {
    const loginUrl = driver.getLoginUrl(returnTo);
    window.location.replace(loginUrl.href);
  }

  const logout = () => {
    const logoutUrl = driver.getLogoutUrl();
    window.location.replace(logoutUrl.href);
    posthog.reset();
  }

  useEffect(() => {
    void init();
  }, []);

  useEffect(() => {
    if (user) {
      posthog.identify(user.email, {
        email: user.email,
      });
    }
  }, [user]);

  if (user === undefined) {
    return <SpinnerPage />;
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        init,
        refreshUser,
        login,
        logout
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};
