import { addToast, ToasterItem } from "@/features/ui/components/toaster/Toaster";
import { useTranslation } from "react-i18next";

export const addLeaveItemErrorToast = () => {
  addToast(<LeaveItemErrorToast />);
};

const LeaveItemErrorToast = () => {
  const { t } = useTranslation();
  return (
    <ToasterItem type="error">
      <span className="material-icons">logout</span>
      <span>{t("explorer.item.actions.leave_toast_error")}</span>
    </ToasterItem>
  );
};
