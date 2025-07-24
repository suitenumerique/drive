import React, { PropsWithChildren, useEffect, useState } from "react";

import { fetchAPI } from "@/features/api/fetchApi";
import { User } from "@/features/auth/types";
import { baseApiUrl } from "../api/utils";
import { APIError } from "../api/APIError";
import { posthog } from "posthog-js";
import { SpinnerPage } from "@/features/ui/components/spinner/SpinnerPage";

export const logout = () => {
  window.location.replace(new URL("logout/", baseApiUrl()).href);
  posthog.reset();
};

export const login = (returnTo?: string) => {
  const url = new URL("authenticate/", baseApiUrl());
  if (returnTo) {
    url.searchParams.set("returnTo", returnTo);
  }
  window.location.replace(url.href);
};

interface AuthContextInterface {
  user?: User | null;
  init?: () => Promise<User | null>;
}

export const AuthContext = React.createContext<AuthContextInterface>({});

export const useAuth = () => React.useContext(AuthContext);

export const Auth = ({
  children,
  redirect,
}: PropsWithChildren & { redirect?: boolean }) => {
  const [user, setUser] = useState<User | null>();

  const init = async () => {
    try {
      const response = await fetchAPI(`users/me/`, undefined, {
        redirectOn40x: false,
      });
      const data = (await response.json()) as User;
      setUser(data);
      return data;
    } catch (error) {
      if (redirect && error instanceof APIError && error.code === 401) {
        login();
      } else {
        setUser(null);
      }
      return null;
    }
  };

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
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};
