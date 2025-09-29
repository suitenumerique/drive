import { useTranslation } from "react-i18next";
import { useAuth } from "../auth/Auth";
import { useConfig } from "../config/ConfigProvider";

/**
 * Hook that opens the feedback widget
 */
export const useMessagesWidget = () => {
  const { t } = useTranslation();
  const { user } = useAuth();
  const { config } = useConfig();

  const apiUrl = config?.FRONTEND_FEEDBACK_MESSAGES_WIDGET_API_URL;
  const widgetPath = config?.FRONTEND_FEEDBACK_MESSAGES_WIDGET_PATH;
  const channel = config?.FRONTEND_FEEDBACK_MESSAGES_WIDGET_CHANNEL;

  const title: string = t("feedback_widget.title");
  const placeholder: string = t("feedback_widget.placeholder");
  const emailPlaceholder: string = t("feedback_widget.email_placeholder");
  const submitText: string = t("feedback_widget.submit_text");
  const successText: string = t("feedback_widget.success_text");
  const successText2: string = t("feedback_widget.success_text2");

  const showWidget = () => {
    if (!channel || !apiUrl || !widgetPath) {
      throw new Error(
        "FRONTEND_FEEDBACK_MESSAGES_WIDGET_API_URL, FRONTEND_FEEDBACK_MESSAGES_WIDGET_PATH or FRONTEND_FEEDBACK_MESSAGES_WIDGET_CHANNEL is not set"
      );
    }

    // Initialize the widget array if it doesn't exist
    if (typeof window !== "undefined" && widgetPath) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (window as any)._stmsg_widget = (window as any)._stmsg_widget || [];

      // Construct script URLs from the base path
      const feedbackScript = `${widgetPath}feedback.js`;

      // Push the widget configuration
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (window as any)._stmsg_widget.push([
        "feedback",
        "init",
        {
          title,
          api: apiUrl,
          channel,
          placeholder,
          emailPlaceholder,
          submitText,
          successText,
          successText2,
          // Add email parameter if user is logged in
          ...(user?.email && { email: user.email }),
        },
      ]);

      // Load the loader script if not already loaded
      if (!document.querySelector(`script[src="${feedbackScript}"]`)) {
        const script = document.createElement("script");
        script.async = true;
        script.src = feedbackScript;
        const firstScript = document.getElementsByTagName("script")[0];
        if (firstScript && firstScript.parentNode) {
          firstScript.parentNode.insertBefore(script, firstScript);
        }
      }
    }
  };

  return { showWidget };
};
