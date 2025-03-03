import { Auth } from "@/features/auth/Auth";

/**
 * This layout is used for the global contexts (auth, etc).
 */
export const GlobalLayout = ({ children }: { children: React.ReactNode }) => {
  return <Auth>{children}</Auth>;
};
