import { Button } from "@openfun/cunningham-react";
import clsx from "clsx";
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
}: {
  children: React.ReactNode;
  closeButton?: boolean;
  className?: string;
  type?: "error" | "info";
} & Partial<ToastContentProps>) => {
  return (
    <div
      className={clsx(
        "suite__toaster__item",
        "suite__toaster__item--" + type,
        className
      )}
    >
      <div className="suite__toaster__item__content">{children}</div>
      {closeButton && (
        <Button
          onClick={closeToast}
          color="primary-text"
          size="small"
          icon={<span className="material-icons">close</span>}
        ></Button>
      )}
    </div>
  );
};

export const addToast = (
  children: React.ReactNode,
  options: Parameters<typeof toast>[1] = {}
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
