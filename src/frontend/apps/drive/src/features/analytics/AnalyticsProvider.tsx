import { useApiConfig } from "../config/useApiConfig";
import { PostHogProvider } from "posthog-js/react";

export const AnalyticsProvider = ({
  children,
}: {
  children: React.ReactNode;
}) => {
  const { data: config } = useApiConfig();

  if (!config?.POSTHOG_KEY) {
    return children;
  }

  return (
    <PostHogProvider
      apiKey={config?.POSTHOG_KEY}
      options={{
        api_host: config?.POSTHOG_HOST,
        defaults: "2025-05-24",
      }}
    >
      {children}
    </PostHogProvider>
  );
};
