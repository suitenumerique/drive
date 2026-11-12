import { Button } from "@gouvfr-lasuite/ui-components";
import { XMark } from "@gouvfr-lasuite/ui-components/icons";
import clsx from "clsx";
import { useTranslation } from "react-i18next";
import { ToastContainer, ToastContentProps, toast } from "react-toastify";

export const Toaster = () => {
  return <ToastContainer />;
};

export const ToasterItem = ({
  children,
  closeToast,
  closeButton = false,
  className,
  type = "info",
  onDrop,
}: {
  children: React.ReactNode;
  closeButton?: boolean;
  className?: string;
  type?: "error" | "info";
  onDrop?: (event: React.DragEvent<HTMLDivElement>) => void;
} & Partial<ToastContentProps>) => {
  const { t } = useTranslation();

  return (
    <div
      onDrop={(event) => onDrop?.(event)}
      className={clsx(
        "suite__toaster__item",
        "suite__toaster__item--" + type,
        className,
      )}
    >
      <div className="suite__toaster__item__content">{children}</div>
      {closeButton && (
        <Button
          onClick={closeToast}
          variant="tertiary"
          size="small"
          icon={<XMark size={16} aria-hidden="true" />}
          aria-label={t("explorer.rightPanel.close")}
        ></Button>
      )}
    </div>
  );
};

export const addToast = (
  children: React.ReactNode,
  options: Parameters<typeof toast>[1] = {},
) => {
  return toast(children, {
    position: "bottom-center",
    closeButton: false,
    className: "suite__toaster__wrapper",
    autoClose: 8000,
    hideProgressBar: true,
    ...options,
  });
};
