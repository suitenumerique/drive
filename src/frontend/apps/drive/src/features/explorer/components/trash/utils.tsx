import { useModals } from "@gouvfr-lasuite/cunningham-react";
import i18n from "@/features/i18n/initI18n";

export const messageModalTrashNavigate = (
  modals: ReturnType<typeof useModals>
) => {
  modals.messageModal({
    title: i18n.t("explorer.trash.navigate.modal.title"),
    children: (
      <div className="clr-greyscale-600">
        {i18n.t("explorer.trash.navigate.modal.description")}
      </div>
    ),
  });
};
