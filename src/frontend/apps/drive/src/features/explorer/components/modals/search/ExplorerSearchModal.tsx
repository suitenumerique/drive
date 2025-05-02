import { Modal, ModalProps, ModalSize } from "@openfun/cunningham-react";
import { useTranslation } from "react-i18next";

import searchImage from "@/assets/search-dev.png";

export const ExplorerSearchModal = (
  props: Pick<ModalProps, "isOpen" | "onClose">
) => {
  const { t } = useTranslation();
  return (
    <Modal
      {...props}
      size={ModalSize.SMALL}
      title={t("explorer.search.modal.title")}
    >
      <div className="explorer__search__modal">
        <p>{t("explorer.search.modal.description")}</p>
        <img src={searchImage.src} alt="" width={200} height={200} />
      </div>
    </Modal>
  );
};
