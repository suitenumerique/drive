import ErrorPage from "next/error";
import { useConfig } from "@/features/config/ConfigProvider";

/**
 * Renders a 404 page instead of its children when the SDK is disabled.
 * Must wrap the whole SDK layout so nothing below mounts (auth, token checks).
 */
export const SdkEnabledGuard = ({
  children,
}: {
  children: React.ReactNode;
}) => {
  const { config } = useConfig();

  if (!config.SDK_ENABLED) {
    return <ErrorPage statusCode={404} />;
  }

  return <>{children}</>;
};
