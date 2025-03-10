import { useQuery } from "@tanstack/react-query";
import { getDriver } from "@/features/config/config";
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
import { useExplorer } from "./ExplorerContext";

type Inputs = {
  title: string;
};

export const ExplorerTree = () => {
  const { t } = useTranslation();
  const driver = getDriver();
  // itemId is the id of the current item
  const { itemId, item } = useExplorer();

  const { data } = useQuery({
    queryKey: ["items"],
    queryFn: () => driver.getItems(),
  });

  const createFolderModal = useModal();

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
      <h4>Explorer Tree</h4>
      <div>
        Current item: {itemId} ( {item?.title} )
        {data?.map((item) => (
          <div key={item.id}>{item.title}</div>
        ))}
      </div>
      <ExplorerCreateFolderModal {...createFolderModal} />
    </div>
  );
};

const ExplorerCreateFolderModal = (
  props: Pick<ModalProps, "isOpen" | "onClose">
) => {
  const { itemId } = useExplorer();
  const { t } = useTranslation();
  const driver = getDriver();

  const { register, handleSubmit } = useForm<Inputs>();
  const onSubmit: SubmitHandler<Inputs> = async (data) => {
    const item = await driver.createFolder({
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
