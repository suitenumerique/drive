import { login, useAuth } from "@/features/auth/Auth";
import { ExplorerTree } from "@/features/explorer/components/ExplorerTree";

export const ExplorerLayout = ({ children }: { children: React.ReactNode }) => {
  const { user } = useAuth();
  if (!user) {
    login();
    return null;
  }
  return (
    <div className="explorer-layout">
      <div className="explorer-layout__sidebar">
        <ExplorerTree />
      </div>
      <div className="explorer-layout__content">
        <div className="explorer-layout__content__inner">{children}</div>
      </div>
    </div>
  );
};
