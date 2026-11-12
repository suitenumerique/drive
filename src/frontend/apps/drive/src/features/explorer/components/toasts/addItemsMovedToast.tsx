import { ArrowRight } from "@gouvfr-lasuite/ui-components/icons";
import { addToast } from "@/features/ui/components/toaster/Toaster";
import { useTranslation } from "react-i18next";
import { ToasterItem } from "@/features/ui/components/toaster/Toaster";

export const addItemsMovedToast = (count: number) => {
  addToast(<ItemsMovedToast count={count} />);
};

const ItemsMovedToast = ({ count }: { count: number }) => {
  const { t } = useTranslation();
  return (
    <ToasterItem>
      <ArrowRight aria-hidden="true" />
      <span>{t("explorer.actions.move.toast", { count })}</span>
    </ToasterItem>
  );
};
