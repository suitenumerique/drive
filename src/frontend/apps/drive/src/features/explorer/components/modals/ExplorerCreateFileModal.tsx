import {
  Button,
  Modal,
  ModalProps,
  ModalSize,
} from "@gouvfr-lasuite/cunningham-react";
import { useTranslation } from "react-i18next";
import { FormProvider, SubmitHandler, useForm } from "react-hook-form";
import { RhfInput } from "@/features/forms/components/RhfInput";
import { Item } from "@/features/drivers/types";
import {
  useMutationCreateFile,
  useMutationCreateFileFromTemplate,
} from "../../hooks/useMutations";
import {
  createBlankOdf,
  BlankOdfExtension,
} from "@/features/encryption/blank-odf/createBlankOdf";

type Inputs = {
  filename: string;
};

export enum ExplorerCreateFileType {
  DOC = "doc",
  POWERPOINT = "powerpoint",
  CALC = "calc",
}

const EXT_BY_TYPE: Record<ExplorerCreateFileType, BlankOdfExtension> = {
  [ExplorerCreateFileType.DOC]: "odt",
  [ExplorerCreateFileType.POWERPOINT]: "odp",
  [ExplorerCreateFileType.CALC]: "ods",
};

const MIME_BY_EXT: Record<BlankOdfExtension, string> = {
  odt: "application/vnd.oasis.opendocument.text",
  ods: "application/vnd.oasis.opendocument.spreadsheet",
  odp: "application/vnd.oasis.opendocument.presentation",
};

export const ExplorerCreateFileModal = (
  props: Pick<ModalProps, "isOpen" | "onClose"> & {
    // Full parent Item. Omit for root / workspace-level creation.
    // When `parent.is_encrypted`, the server can't provide a plaintext
    // template (it has no access to the parent's keys), so we generate a
    // blank ODF client-side and route through `createFile`, which encrypts
    // and uploads via the same path as drag-drop.
    parent?: Item;
    type: ExplorerCreateFileType;
  }
) => {
  const { t } = useTranslation();
  const form = useForm<Inputs>();
  const createFileFromTemplate = useMutationCreateFileFromTemplate();
  const createFile = useMutationCreateFile();

  const onSubmit: SubmitHandler<Inputs> = async (data) => {
    const extension = EXT_BY_TYPE[props.type];
    const filename = data.filename.endsWith(`.${extension}`)
      ? data.filename
      : `${data.filename}.${extension}`;

    const onSuccess = () => {
      form.reset();
      props.onClose();
    };

    if (props.parent?.is_encrypted) {
      const bytes = await createBlankOdf(extension);
      const blankFile = new File([bytes], filename, {
        type: MIME_BY_EXT[extension],
      });
      createFile.mutate(
        { parent: props.parent, filename, file: blankFile },
        { onSuccess },
      );
      return;
    }

    createFileFromTemplate.mutate(
      {
        parentId: props.parent?.id,
        extension,
        title: data.filename,
      },
      { onSuccess },
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
