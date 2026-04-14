import {
  Button,
  Modal,
  ModalProps,
  ModalSize,
} from "@gouvfr-lasuite/cunningham-react";
import { useTranslation } from "react-i18next";
import { FormProvider, SubmitHandler, useForm } from "react-hook-form";
import { RhfInput } from "@/features/forms/components/RhfInput";
import { useMutationCreateFileFromTemplate } from "../../hooks/useMutations";
import { useRouter } from "next/router";
import { useSetSelectedItems } from "../../stores/selectionStore";

type Inputs = {
  filename: string;
};

export enum ExplorerCreateFileType {
  DOC = "doc",
  POWERPOINT = "powerpoint",
  CALC = "calc",
}

const getExtension = (type: ExplorerCreateFileType) => {
  switch (type) {
    case ExplorerCreateFileType.DOC:
      return "odt";
    case ExplorerCreateFileType.POWERPOINT:
      return "odp";
    case ExplorerCreateFileType.CALC:
      return "ods";
  }
};

export const ExplorerCreateFileModal = (
  props: Pick<ModalProps, "isOpen" | "onClose"> & {
    parentId?: string;
    redirectAfterCreate?: boolean;
    type: ExplorerCreateFileType;
  }
) => {
  const { t } = useTranslation();
  const form = useForm<Inputs>();
  const createFileFromTemplate = useMutationCreateFileFromTemplate();
  const router = useRouter();
  const setSelectedItems = useSetSelectedItems();

  const onSubmit: SubmitHandler<Inputs> = async (data) => {
    const extension = getExtension(props.type);

    createFileFromTemplate.mutate(
      {
        parentId: props.parentId,
        extension: extension,
        title: data.filename,
      },
      {
        onSuccess: (createdItem) => {
          form.reset();
          props.onClose();
          if (props.redirectAfterCreate && createdItem?.id) {
            router.push(`/explorer/items/my-files`);
            setSelectedItems([createdItem]);
          }
        },
      }
    );
  };

  return (
    <Modal
      {...props}
      size={ModalSize.SMALL}
      title={t(`explorer.actions.createFile.modal.title_${props.type}`)}
      rightActions={
        <>
          <Button variant="bordered" onClick={props.onClose}>
            {t("explorer.actions.createFile.modal.cancel")}
          </Button>
          <Button type="submit" form="create-file-form">
            {t("explorer.actions.createFile.modal.submit")}
          </Button>
        </>
      }
    >
      <FormProvider {...form}>
        <form
          onSubmit={form.handleSubmit(onSubmit)}
          id="create-file-form"
          className="mt-s"
        >
          <RhfInput
            label={t("explorer.actions.createFile.modal.label")}
            fullWidth={true}
            autoFocus={true}
            {...form.register("filename")}
          />
        </form>
      </FormProvider>
    </Modal>
  );
};
