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

export const ExplorerEditWorkspaceModal = (
  props: Pick<ModalProps, "isOpen" | "onClose"> & {
    item: Item;
  }
) => {
  const { t } = useTranslation();
  const updateWorkspace = useMutationUpdateWorkspace();

  const onSubmit: SubmitHandler<WorkspaceFormInputs> = async (data) => {
    updateWorkspace.mutate({
      id: props.item.id,
      ...data,
    });
    props.onClose();
  };

  return (
    <Modal
      {...props}
      size={ModalSize.MEDIUM}
      title={t("explorer.actions.createWorkspace.modal.title")}
      rightActions={
        <>
          <Button color="secondary" onClick={props.onClose}>
            {t("explorer.actions.createWorkspace.modal.cancel")}
          </Button>
          <Button type="submit" form="workspace-form">
            {t("explorer.actions.createWorkspace.modal.submit")}
          </Button>
        </>
      }
    >
      <div className="clr-greyscale-600 fs-s m-0">
        {t("explorer.actions.createWorkspace.modal.description")}
      </div>
      <WorkspaceForm item={props.item} onSubmit={onSubmit} />
    </Modal>
  );
};
