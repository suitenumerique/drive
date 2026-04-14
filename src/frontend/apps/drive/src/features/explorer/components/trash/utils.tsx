import {
  ModalSize,
  useModals,
  VariantType,
} from "@gouvfr-lasuite/cunningham-react";
import i18n from "@/features/i18n/initI18n";

export const messageModalTrashNavigate = (
  modals: ReturnType<typeof useModals>,
  isFile: boolean = false,
) => {
  const key = isFile ? "modal_file" : "modal_folder";
  modals.messageModal({
    messageType: VariantType.INFO,
    size: ModalSize.MEDIUM,
    title: i18n.t(`explorer.trash.navigate.${key}.title`),
    children: (
      <div className="clr-greyscale-600">
        {i18n.t(`explorer.trash.navigate.${key}.description`)}
      </div>
    ),
  });
};
