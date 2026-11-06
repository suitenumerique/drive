import {
  Button,
  Modal,
  ModalProps,
  ModalSize,
  removeFileExtension,
} from "@gouvfr-lasuite/ui-components";
import { useTranslation } from "react-i18next";
import { FormProvider, SubmitHandler, useForm } from "react-hook-form";
import { Item } from "@/features/drivers/types";
import { getRestrictionTarget } from "@/features/drivers/utils";
import { RhfInput } from "@/features/forms/components/RhfInput";
import { useMutationRenameItem } from "../../hooks/useMutations";
import { useRef } from "react";
import { useTreeUtils } from "../../hooks/useTreeUtils";
import { useGlobalExplorer } from "../GlobalExplorerContext";
import { useSelectionStore } from "../../stores/selectionStore";
import { useUpdateItemInPaginatedList } from "../../hooks/useOptimisticPagination";

type Inputs = {
  title: string;
};

export const ExplorerRenameItemModal = (
  props: Pick<ModalProps, "isOpen" | "onClose"> & {
    item: Item;
  },
) => {
  const treeUtils = useTreeUtils();
  const { rightPanelOpen, rightPanelForcedItem, setRightPanelForcedItem } =
    useGlobalExplorer();
  const selectionStore = useSelectionStore();
  const { t } = useTranslation();
  const form = useForm<Inputs>({
    defaultValues: {
      title: removeFileExtension(props.item.title),
    },
  });

  const updateItem = useMutationRenameItem();
  const updateItemInPaginatedList = useUpdateItemInPaginatedList();
  // A restriction entry shows its folder's title: rename the folder itself.
  const renamedId = getRestrictionTarget(props.item)?.id ?? props.item.id;

  const onSubmit: SubmitHandler<Inputs> = async (data) => {
    await updateItem.mutateAsync(
      {
        ...data,
        id: renamedId,
      },
      {
        onSuccess: () => {
          treeUtils.updateNodeByOriginalId(renamedId, {
            title: data.title,
          });
          if (props.item.target && renamedId !== props.item.id) {
            // The mutation only refreshes the folder, the entry mirrors it.
            // Drops on the entry read its target, so rename both.
            const entryUpdate = {
              title: data.title,
              target: { ...props.item.target, title: data.title },
            };
            treeUtils.updateNodeByOriginalId(props.item.id, entryUpdate);
            updateItemInPaginatedList(["items"], props.item.id, entryUpdate);
          }

          const selectedItem =
            rightPanelForcedItem ?? selectionStore.getSelectedItems()[0];

          if (rightPanelOpen && selectedItem?.id === props.item.id) {
            const newRightPanelForcedItem = {
              ...selectedItem,
              title: data.title,
            };

            setRightPanelForcedItem(newRightPanelForcedItem);
          }
        },
      },
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
          <Button variant="bordered" onClick={props.onClose}>
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
