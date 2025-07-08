import { Item } from "@/features/drivers/types";
import { ItemIcon } from "../icons/ItemIcon";
import { Button, useModal } from "@openfun/cunningham-react";
import { useExplorer } from "../ExplorerContext";
import { InfoRow } from "@/features/ui/components/info/InfoRow";
import { useTranslation } from "react-i18next";

import multipleSelection from "@/assets/mutliple-selection.png";
import emptySelection from "@/assets/empty-selection.png";
import { itemIsWorkspace } from "@/features/drivers/utils";
import { IconSize } from "@gouvfr-lasuite/ui-kit";
import { WorkspaceShareModal } from "../modals/share/WorkspaceShareModal";
import { ItemInfo } from "@/features/items/components/ItemInfo";

type ExplorerRightPanelContentProps = {
  item?: Item;
};

export const ExplorerRightPanelContent = ({
  item,
}: ExplorerRightPanelContentProps) => {
  const { setRightPanelOpen, selectedItems } = useExplorer();
  const shareModal = useModal();
  const { t } = useTranslation();

  const firstSelectedItem = item ?? selectedItems[0];
  const isWorkspace = firstSelectedItem
    ? itemIsWorkspace(firstSelectedItem)
    : false;

  if (!firstSelectedItem) {
    return (
      <div className="explorer__right-panel__empty-selection">
        <div className="explorer__right-panel__multiple-selection__close">
          <Button
            size="small"
            color="primary-text"
            icon={<span className="material-icons">close</span>}
            onClick={() => setRightPanelOpen(false)}
          />
        </div>
        <img
          src={emptySelection.src}
          alt={t("explorer.rightPanel.empty.alt")}
        />
        <div className="explorer__right-panel__empty__text">
          {t("explorer.rightPanel.empty.text")}
        </div>
      </div>
    );
  }

  if (selectedItems.length > 1) {
    return (
      <div className="explorer__right-panel__multiple-selection">
        <div className="explorer__right-panel__multiple-selection__close">
          <Button
            size="small"
            color="primary-text"
            icon={<span className="material-icons">close</span>}
            onClick={() => setRightPanelOpen(false)}
          />
        </div>
        <img src={multipleSelection.src} alt={selectedItems[0].title} />
        <div className="explorer__right-panel__multiple-selection__text">
          {t("explorer.rightPanel.multipleSelection.text")}
        </div>
      </div>
    );
  }

  return (
    <>
      <div className="explorer__right-panel">
        <div className="explorer__right-panel__section p">
          <div className="explorer__right-panel__item-title">
            <div className="explorer__right-panel__item-title__close">
              <Button
                size="small"
                color="primary-text"
                icon={<span className="material-icons">close</span>}
                onClick={() => setRightPanelOpen(false)}
              />
            </div>
            <div className="explorer__right-panel__item-title__icon">
              <ItemIcon
                item={firstSelectedItem}
                size={IconSize.SMALL}
                type="mini"
              />
            </div>
            <div className="explorer__right-panel__item-title__text">
              {firstSelectedItem.title}
            </div>
          </div>
          <div className="explorer__right-panel__item-type">
            <ItemIcon item={firstSelectedItem} size={IconSize.X_LARGE} />
          </div>
          {isWorkspace && (
            <InfoRow
              label={t("explorer.rightPanel.sharing")}
              rightContent={
                firstSelectedItem?.nb_accesses &&
                firstSelectedItem?.nb_accesses > 1 ? (
                  <Button
                    color="tertiary"
                    icon={<span className="material-icons">group</span>}
                    onClick={shareModal.open}
                  >
                    {firstSelectedItem?.nb_accesses}
                  </Button>
                ) : (
                  <Button color="primary-text" onClick={shareModal.open}>
                    {t("explorer.rightPanel.share")}
                  </Button>
                )
              }
            />
          )}
        </div>
        <ItemInfo item={firstSelectedItem} />
      </div>
      {firstSelectedItem && isWorkspace && shareModal.isOpen && (
        <WorkspaceShareModal
          isOpen={shareModal.isOpen}
          onClose={shareModal.close}
          item={firstSelectedItem}
        />
      )}
    </>
  );
};
