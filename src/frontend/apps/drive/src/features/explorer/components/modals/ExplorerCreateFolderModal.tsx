import {
  Button,
  Modal,
  ModalProps,
  ModalSize,
} from "@gouvfr-lasuite/ui-components";
import { useTranslation } from "react-i18next";
import { FormProvider, SubmitHandler, useForm } from "react-hook-form";
import { RhfInput } from "@/features/forms/components/RhfInput";
import { Item } from "@/features/drivers/types";
import { useMutationCreateFolder } from "../../hooks/useMutations";
import { useRouter } from "next/router";
import { useSetSelectedItems } from "../../stores/selectionStore";

type Inputs = {
  title: string;
};

type ExplorerCreateFolderModalProps = Pick<ModalProps, "isOpen" | "onClose"> & {
  // Full parent Item. Omit for root / workspace-level creation.
  // When `parent.is_encrypted`, the driver mints a wrapped folder key.
  parent?: Item;
  redirectAfterCreate?: boolean;
};

export const ExplorerCreateFolderModal = ({
  ...props
}: ExplorerCreateFolderModalProps) => {
  const { t } = useTranslation();
  const form = useForm<Inputs>();
  const createFolder = useMutationCreateFolder();
  const router = useRouter();
  const setSelectedItems = useSetSelectedItems();

  const onSubmit: SubmitHandler<Inputs> = async (data) => {
    form.reset();
    createFolder.mutate(
      {
        ...data,
        parent: props.parent,
      },
      {
        onSuccess: (createdItem) => {
          form.reset();
          props.onClose();
          if (props.redirectAfterCreate && createdItem?.id) {
            router.push(`/explorer/items/${createdItem.id}`);
            setSelectedItems([createdItem]);
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
