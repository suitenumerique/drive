import { useConfig } from "../config/ConfigProvider";
import { PostHogProvider } from "posthog-js/react";

export const AnalyticsProvider = ({
  children,
}: {
  children: React.ReactNode;
}) => {
  const { config } = useConfig();

  if (!config?.POSTHOG_KEY) {
    return children;
  }

  return (
    <PostHogProvider
      apiKey={config?.POSTHOG_KEY}
      options={{
        api_host: config?.POSTHOG_HOST,
        defaults: "2025-05-24",
        opt_out_useragent_filter:
          process.env.NEXT_PUBLIC_POSTHOG_TEST_MODE === "true",
        request_batching:
          process.env.NEXT_PUBLIC_POSTHOG_TEST_MODE !== "true",
      }}
    >
      {children}
    </PostHogProvider>
  );
};
