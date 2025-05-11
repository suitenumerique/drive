import { Button, useModal } from "@openfun/cunningham-react";
import { ExplorerSearchModal } from "./modals/search/ExplorerSearchModal";
import { useTranslation } from "react-i18next";
export const ExplorerSearchButton = () => {
  const searchModal = useModal();
  const { t } = useTranslation();
  return (
    <>
      <ExplorerSearchModal {...searchModal} />
      <Button
        color="primary-text"
        aria-label={t("explorer.tree.search")}
        icon={<span className="material-icons">search</span>}
        onClick={searchModal.open}
        className="explorer__search__button"
      />
    </>
  );
};
