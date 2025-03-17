import { useMutation, useQueryClient } from "@tanstack/react-query";
import { getDriver } from "@/features/config/Config";
import {
  Button,
  Input,
  Modal,
  ModalProps,
  ModalSize,
  useModal,
} from "@openfun/cunningham-react";
import { useTranslation } from "react-i18next";
import { SubmitHandler, useForm } from "react-hook-form";
import { NavigationEventType, useExplorer } from "./ExplorerContext";
import { Item } from "@/features/drivers/types";

type Inputs = {
  title: string;
};

export const ExplorerTree = () => {
  const { t } = useTranslation();

  // itemId is the id of the current item
  const { item, tree, onNavigate } = useExplorer();

  const createFolderModal = useModal();

  const drawTreeDuPauvre = (treeItem: Item) => {
    return (
      <div key={treeItem.id}>
        <div
          style={{
            fontWeight: treeItem.id === item?.id ? "bold" : "normal",
            cursor: "pointer",
          }}
          onClick={() =>
            onNavigate({
              type: NavigationEventType.ITEM,
              item: treeItem,
            })
          }
        >
          {treeItem.title}
        </div>
        <div
          style={{
            paddingLeft: "2rem",
          }}
        >
          {treeItem.children?.map((child) => drawTreeDuPauvre(child))}
        </div>
      </div>
    );
  };

  return (
    <div>
      <div className="explorer__tree__actions">
        <div className="explorer__tree__actions__left">
          <Button
            icon={<span className="material-icons">add</span>}
            onClick={createFolderModal.open}
          >
            {t("explorer.tree.createFolder")}
          </Button>
          <Button color="secondary">{t("explorer.tree.import")}</Button>
        </div>
        <Button
          color="primary-text"
          aria-label={t("explorer.tree.search")}
          icon={<span className="material-icons">search</span>}
        ></Button>
      </div>
      <div
        style={{
          padding: "12px",
        }}
      >
        {tree && drawTreeDuPauvre(tree)}
      </div>
      <ExplorerCreateFolderModal {...createFolderModal} />
    </div>
  );
};

/**
 * TODO: Create dedicated file.
 */
const ExplorerCreateFolderModal = (
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
