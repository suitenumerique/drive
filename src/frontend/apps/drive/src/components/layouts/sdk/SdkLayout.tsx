import { Auth } from "@/core/auth/Auth";

export const SdkLayout = ({ children }: { children: React.ReactNode }) => {
  return <Auth>{children}</Auth>;
};
