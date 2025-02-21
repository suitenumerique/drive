import React, { PropsWithChildren, useEffect, useState } from "react";

import { fetchAPI } from "@/core/api/fetchApi";
import { User } from "@/core/auth/types";
import { baseApiUrl } from "@/core/conf";

export const logout = () => {
  window.location.replace(new URL("logout/", baseApiUrl()).href);
};

export const login = () => {
  window.location.replace(new URL("authenticate/", baseApiUrl()).href);
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
    const response = await fetchAPI(`users/me/`, undefined, {
      logoutOn401: false,
    });
    if (!response.ok) {
      if (redirect) {
        login();
      } else {
        setUser(null);
      }
      return null;
    }
    const data = (await response.json()) as User;
    setUser(data);
    return data;
  };

  useEffect(() => {
    void init();
  }, []);

  if (user === undefined) {
    return (
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          height: "100vh",
        }}
      >
        <div>LOADING</div>
      </div>
    );
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
