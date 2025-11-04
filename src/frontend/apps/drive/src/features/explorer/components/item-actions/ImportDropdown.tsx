import { DropdownMenu, useDropdownMenu } from "@gouvfr-lasuite/ui-kit";
import uploadFileSvg from "@/assets/icons/upload_file.svg";
import uploadFolderSvg from "@/assets/icons/upload_folder.svg";
import { useTranslation } from "react-i18next";
export type ImportDropdownProps = {
  trigger: React.ReactNode;
  importMenu: ReturnType<typeof useDropdownMenu>;
};

export const ImportDropdown = ({
  trigger,
  importMenu,
}: ImportDropdownProps) => {
  const { t } = useTranslation();
  return (
    <DropdownMenu
      options={[
        {
          icon: <img src={uploadFileSvg.src} alt="" />,
          label: t("explorer.tree.import.files"),
          value: "info",
          callback: () => {
            document.getElementById("import-files")?.click();
          },
        },
        {
          icon: <img src={uploadFolderSvg.src} alt="" />,
          label: t("explorer.tree.import.folders"),
          value: "info",
          callback: () => {
            document.getElementById("import-folders")?.click();
          },
        },
      ]}
      {...importMenu}
      onOpenChange={importMenu.setIsOpen}
    >
      {trigger}
    </DropdownMenu>
  );
};
