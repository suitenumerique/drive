import {
  addToast,
  ToasterItem,
} from "@/features/ui/components/toaster/Toaster";
import { useMutationRestoreItems } from "../../hooks/useMutations";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { DropdownMenu } from "@gouvfr-lasuite/ui-kit";
import { Button } from "@openfun/cunningham-react";
import undoIcon from "@/assets/icons/undo.svg";

import { ExplorerGridActionsCellProps } from "./ExplorerGridActionsCell";

export const ExplorerGridTrashActionsCell = (
  params: ExplorerGridActionsCellProps
) => {
  const item = params.row.original;
  const [isOpen, setIsOpen] = useState(false);
  const { t } = useTranslation();
  const restoreItem = useMutationRestoreItems();

  const handleRestore = async () => {
    addToast(
      <ToasterItem>
        <span className="material-icons">delete</span>
        <span>{t("explorer.actions.restore.toast", { count: 1 })}</span>
      </ToasterItem>
    );
    await restoreItem.mutateAsync([item.id]);
  };

  return (
    <>
      <DropdownMenu
        options={[
          {
            icon: <img src={undoIcon.src} alt="info" width={24} height={24} />,
            label: t("explorer.grid.actions.restore"),
            value: "restore",
            callback: handleRestore,
          },
          //   {
          //     icon: (
          //       <img src={deleteIcon.src} alt="info" width={24} height={24} />
          //     ),
          //     label: t("explorer.grid.actions.hard_delete"),
          //     value: "hard_delete",
          //     callback: () => alert("Partager"),
          //   },
        ]}
        isOpen={isOpen}
        onOpenChange={setIsOpen}
      >
        <Button
          onClick={() => setIsOpen(!isOpen)}
          color="primary-text"
          className="c__language-picker"
          icon={<span className="material-icons">more_horiz</span>}
        ></Button>
      </DropdownMenu>
    </>
  );
};
