import { useMutation } from "@tanstack/react-query";
import {
  Button,
  Input,
  Modal,
  ModalProps,
  ModalSize,
} from "@openfun/cunningham-react";
import { useExplorer } from "../ExplorerContext";
import { useTranslation } from "react-i18next";
import { useQueryClient } from "@tanstack/react-query";
import { SubmitHandler, useForm } from "react-hook-form";
import { getDriver } from "@/features/config/Config";

type Inputs = {
  title: string;
};

export const ExplorerCreateFolderModal = (
  props: Pick<ModalProps, "isOpen" | "onClose">
) => {
  const { itemId } = useExplorer();
  const { t } = useTranslation();
  const driver = getDriver();
  const { register, handleSubmit } = useForm<Inputs>();

  const queryClient = useQueryClient();
  const createFolder = useMutation({
    mutationFn: (...payload: Parameters<typeof driver.createFolder>) => {
      return driver.createFolder(...payload);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["items", itemId],
      });
    },
  });

  const onSubmit: SubmitHandler<Inputs> = async (data) => {
    createFolder.mutate({
      ...data,
      parentId: itemId,
    });
    props.onClose();
  };

  return (
    <Modal
      {...props}
      size={ModalSize.SMALL}
      title={t("explorer.actions.createFolder.modal.title")}
      rightActions={
        <>
          <Button color="secondary" onClick={props.onClose}>
            {t("explorer.actions.createFolder.modal.cancel")}
          </Button>
          <Button type="submit" form="create-folder-form">
            {t("explorer.actions.createFolder.modal.submit")}
          </Button>
        </>
      }
    >
      <form
        onSubmit={handleSubmit(onSubmit)}
        id="create-folder-form"
        className="mt-s"
      >
        <Input
          label={t("explorer.actions.createFolder.modal.label")}
          fullWidth={true}
          {...register("title")}
        />
      </form>
    </Modal>
  );
};
