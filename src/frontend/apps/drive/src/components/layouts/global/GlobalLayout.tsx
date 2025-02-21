import { Auth, login, logout, useAuth } from "@/core/auth/Auth";

export const GlobalLayout = ({ children }: { children: React.ReactNode }) => {
  return (
    <Auth>
      <Navbar />
      {children}
    </Auth>
  );
};

const Navbar = () => {
  const { user } = useAuth();
  return (
    <nav>
      NAVBAR
      {user ? (
        <div>
          Welcome {user.email}
          <button onClick={logout}>Logout</button>
        </div>
      ) : (
        <div>
          <div>Not logged in</div>
          <button onClick={login}>Login</button>
        </div>
      )}
    </nav>
  );
};
