import {
  ModalSize,
  useModals,
  VariantType,
} from "@gouvfr-lasuite/ui-components";
import i18n from "@/features/i18n/initI18n";

export const messageModalTrashNavigate = (
  modals: ReturnType<typeof useModals>,
  kind: "folder" | "file" | "link" = "folder",
) => {
  const key = `modal_${kind}`;
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
