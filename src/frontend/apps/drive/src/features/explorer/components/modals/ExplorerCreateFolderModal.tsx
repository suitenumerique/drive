import {
  Button,
  Modal,
  ModalProps,
  ModalSize,
} from "@openfun/cunningham-react";
import { useTranslation } from "react-i18next";
import { FormProvider, SubmitHandler, useForm } from "react-hook-form";
import { RhfInput } from "@/features/forms/components/RhfInput";
import { useMutationCreateFolder } from "../../hooks/useMutations";
import { itemToTreeItem } from "../GlobalExplorerContext";
import { useTreeContext } from "@gouvfr-lasuite/ui-kit";

type Inputs = {
  title: string;
};

export const ExplorerCreateFolderModal = (
  props: Pick<ModalProps, "isOpen" | "onClose"> & {
    parentId: string;
  }
) => {
  const { t } = useTranslation();
  const form = useForm<Inputs>();
  const createFolder = useMutationCreateFolder();
  const treeContext = useTreeContext();

  const onSubmit: SubmitHandler<Inputs> = async (data) => {
    form.reset();
    createFolder.mutate(
      {
        ...data,
        parentId: props.parentId,
      },
      {
        onSuccess: (data) => {
          treeContext?.treeData.addChild(
            props.parentId,
            itemToTreeItem(data),
            0
          );
          form.reset();
          props.onClose();
        },
      }
    );
  };

  return (
    <Modal
      {...props}
      size={ModalSize.SMALL}
      title={t("explorer.actions.createFolder.modal.title")}
      rightActions={
        <>
          <Button variant="bordered" onClick={props.onClose}>
            {t("explorer.actions.createFolder.modal.cancel")}
          </Button>
          <Button type="submit" form="create-folder-form">
            {t("explorer.actions.createFolder.modal.submit")}
          </Button>
        </>
      }
    >
      <FormProvider {...form}>
        <form
          onSubmit={form.handleSubmit(onSubmit)}
          id="create-folder-form"
          className="mt-s"
        >
          <RhfInput
            label={t("explorer.actions.createFolder.modal.label")}
            fullWidth={true}
            autoFocus={true}
            {...form.register("title")}
          />
        </form>
      </FormProvider>
    </Modal>
  );
};
