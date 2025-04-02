import {
  Button,
  Modal,
  ModalProps,
  ModalSize,
} from "@openfun/cunningham-react";
import { useTranslation } from "react-i18next";
import { SubmitHandler, useForm } from "react-hook-form";
import { WorkspaceForm } from "./WorkspaceForm";
import { useMutationCreateWorskpace } from "@/features/explorer/hooks/useMutations";

type Inputs = {
  title: string;
  description: string;
};

export const ExplorerCreateWorkspaceModal = (
  props: Pick<ModalProps, "isOpen" | "onClose">
) => {
  const { t } = useTranslation();
  const form = useForm<Inputs>();
  const createWorkspace = useMutationCreateWorskpace();

  const onSubmit: SubmitHandler<Inputs> = async (data) => {
    form.reset();
    createWorkspace.mutate({
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
          <Button type="submit" form="create-folder-form">
            {t("explorer.actions.createWorkspace.modal.submit")}
          </Button>
        </>
      }
    >
      <div className="clr-greyscale-600 fs-s m-0">
        {t("explorer.actions.createWorkspace.modal.description")}
      </div>
      <WorkspaceForm onSubmit={onSubmit} />
    </Modal>
  );
};
