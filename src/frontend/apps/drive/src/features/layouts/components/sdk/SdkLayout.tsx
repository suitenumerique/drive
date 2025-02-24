import { Auth } from "@/features/auth/Auth";

export const SdkLayout = ({ children }: { children: React.ReactNode }) => {
  return <Auth>{children}</Auth>;
};
