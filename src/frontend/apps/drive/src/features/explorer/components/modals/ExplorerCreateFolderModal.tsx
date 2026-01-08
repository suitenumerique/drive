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
import { useRouter } from "next/router";

type Inputs = {
  title: string;
};

type ExplorerCreateFolderModalProps = Pick<ModalProps, "isOpen" | "onClose"> & {
  parentId?: string;
  canCreateChildren?: boolean;
};

export const ExplorerCreateFolderModal = ({
  canCreateChildren = true,
  ...props
}: ExplorerCreateFolderModalProps) => {
  const { t } = useTranslation();
  const form = useForm<Inputs>();
  const createFolder = useMutationCreateFolder();
  const router = useRouter();

  const onSubmit: SubmitHandler<Inputs> = async (data) => {
    form.reset();
    createFolder.mutate(
      {
        ...data,
        parentId: canCreateChildren ? props.parentId : undefined,
      },
      {
        onSuccess: () => {
          form.reset();
          props.onClose();
          if (!props.parentId || !canCreateChildren) {
            router.push(`/explorer/items/my_files`);
          }
        },
      },
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
            data-testid="create-folder-input"
            autoFocus={true}
            {...form.register("title")}
          />
        </form>
      </FormProvider>
    </Modal>
  );
};
