import React, { PropsWithChildren, useEffect, useState } from "react";

import { fetchAPI } from "@/features/api/fetchApi";
import { User } from "@/features/auth/types";
import { baseApiUrl } from "../api/utils";
import { APIError } from "../api/APIError";

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
    try {
      const response = await fetchAPI(`users/me/`, undefined, {
        logoutOn401: false,
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
