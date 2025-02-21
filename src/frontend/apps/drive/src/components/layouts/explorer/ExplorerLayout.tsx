import { login, useAuth } from "@/core/auth/Auth";

export const ExplorerLayout = ({ children }: { children: React.ReactNode }) => {
  const { user } = useAuth();
  if (!user) {
    login();
    return null;
  }
  return (
    <div className="explorer-layout">
      <div className="explorer-layout__sidebar">SIDEBAR</div>
      <div className="explorer-layout__content">
        <div className="explorer-layout__content__inner">{children}</div>
      </div>
    </div>
  );
};
