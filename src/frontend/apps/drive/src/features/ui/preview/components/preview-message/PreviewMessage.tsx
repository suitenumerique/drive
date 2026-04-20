import clsx from "clsx";
import React from "react";

interface PreviewMessageProps {
  icon: React.ReactNode;
  title: React.ReactNode;
  description?: React.ReactNode;
  action?: React.ReactNode;
  variant?: "neutral" | "error";
  closeOnBackdrop?: boolean;
}

export const PreviewMessage = ({
  icon,
  title,
  description,
  action,
  variant = "neutral",
  closeOnBackdrop = true,
}: PreviewMessageProps) => {
  return (
    <div
      className={clsx(
        "preview-message",
        variant === "error" && "preview-message--error",
      )}
      data-preview-backdrop={closeOnBackdrop ? "true" : undefined}
    >
      <div className="preview-message__icon">{icon}</div>
      <p className="preview-message__title">{title}</p>
      {description && (
        <p className="preview-message__description">{description}</p>
      )}
      {action && <div className="preview-message__action">{action}</div>}
    </div>
  );
};
