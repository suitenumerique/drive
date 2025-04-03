import {
  Button,
  Modal,
  ModalProps,
  ModalSize,
} from "@openfun/cunningham-react";
import { useTranslation } from "react-i18next";

import { Item } from "@/features/drivers/types";
import { WorkspaceForm, WorkspaceFormInputs } from "./WorkspaceForm";
import { useMutationUpdateWorkspace } from "@/features/explorer/hooks/useMutations";
import { SubmitHandler } from "react-hook-form";
import { useTreeContext } from "@gouvfr-lasuite/ui-kit";
import { useExplorer } from "../../ExplorerContext";

export const ExplorerEditWorkspaceModal = (
  props: Pick<ModalProps, "isOpen" | "onClose"> & {
    item: Item;
  }
) => {
  const { t } = useTranslation();
  const treeContext = useTreeContext<Item>();
  const { setRightPanelForcedItem, rightPanelForcedItem, rightPanelOpen } =
    useExplorer();
  const updateWorkspace = useMutationUpdateWorkspace();

  const onSubmit: SubmitHandler<WorkspaceFormInputs> = async (data) => {
    updateWorkspace.mutate(
      {
        id: props.item.id,
        ...data,
      },
      {
        onSuccess: () => {
          const updatedItem = {
            ...props.item,
            title: data.title,
            description: data.description,
          };
          treeContext?.treeData.updateNode(props.item.id, updatedItem);
          if (rightPanelOpen && rightPanelForcedItem?.id === props.item.id) {
            setRightPanelForcedItem(updatedItem);
          }
          props.onClose();
        },
      }
    );
  };

  return (
    <Modal
      {...props}
      size={ModalSize.MEDIUM}
      closeOnClickOutside
      title={t("explorer.workspaces.edit.title")}
      rightActions={
        <>
          <Button color="secondary" onClick={props.onClose}>
            {t("explorer.workspaces.edit.cancel")}
          </Button>
          <Button type="submit" form="workspace-form">
            {t("explorer.workspaces.edit.submit")}
          </Button>
        </>
      }
    >
      <div className="clr-greyscale-600 fs-s m-0">
        {t("explorer.workspaces.edit.description")}
      </div>
      <WorkspaceForm item={props.item} onSubmit={onSubmit} />
    </Modal>
  );
};
