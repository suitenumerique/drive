import {
  Button,
  Modal,
  ModalProps,
  ModalSize,
} from "@openfun/cunningham-react";
import { useTranslation } from "react-i18next";
import { FormProvider, SubmitHandler, useForm } from "react-hook-form";
import { Item } from "@/features/drivers/types";
import { RhfInput } from "@/features/forms/components/RhfInput";
import { useMutationRenameItem } from "../../hooks/useMutations";
import { useRef } from "react";
import { useTreeContext } from "@gouvfr-lasuite/ui-kit";
import { removeFileExtension } from "../../utils/mimeTypes";

type Inputs = {
  title: string;
};

export const ExplorerRenameItemModal = (
  props: Pick<ModalProps, "isOpen" | "onClose"> & {
    item: Item;
  }
) => {
  const treeContext = useTreeContext<Item>();
  const { t } = useTranslation();
  const form = useForm<Inputs>({
    defaultValues: {
      title: removeFileExtension(props.item.title),
    },
  });

  const updateItem = useMutationRenameItem();

  const onSubmit: SubmitHandler<Inputs> = async (data) => {
    await updateItem.mutateAsync(
      {
        ...data,
        id: props.item.id,
      },
      {
        onSuccess: () => {
          treeContext?.treeData.updateNode(props.item.id, {
            title: data.title,
          });
        },
      }
    );

    props.onClose();
  };

  const inputRef = useRef<HTMLInputElement>(null);
  const inputRegister = form.register("title");

  return (
    <Modal
      {...props}
      size={ModalSize.SMALL}
      title={t("explorer.actions.rename.modal.title")}
      rightActions={
        <>
          <Button color="secondary" onClick={props.onClose}>
            {t("explorer.actions.rename.modal.cancel")}
          </Button>
          <Button type="submit" form="rename-item-form">
            {t("explorer.actions.rename.modal.submit")}
          </Button>
        </>
      }
    >
      <FormProvider {...form}>
        <form
          onSubmit={form.handleSubmit(onSubmit)}
          id="rename-item-form"
          className="mt-s"
        >
          <RhfInput
            label={t("explorer.actions.rename.modal.label")}
            type="text"
            {...inputRegister}
            ref={(e) => {
              inputRegister.ref(e);
              if (!inputRef.current) {
                e?.focus();
                e?.setSelectionRange(0, e.value.length);
                // We only set the ref once because it sometimes call this function with e === null, don't know why,
                // but it causes setSelectionRange to be called frenetically.
                inputRef.current = e;
              }
            }}
          />
        </form>
      </FormProvider>
    </Modal>
  );
};
