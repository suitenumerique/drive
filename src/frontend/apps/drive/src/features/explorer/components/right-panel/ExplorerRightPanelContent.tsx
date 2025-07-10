import { Item } from "@/features/drivers/types";
import { ItemIcon } from "../icons/ItemIcon";
import { Button, useModal } from "@openfun/cunningham-react";
import { useGlobalExplorer } from "../GlobalExplorerContext";
import { InfoRow } from "@/features/ui/components/info/InfoRow";
import { useTranslation } from "react-i18next";

import multipleSelection from "@/assets/mutliple-selection.png";
import emptySelection from "@/assets/empty-selection.png";
import { getFormatTranslationKey } from "../../utils/mimeTypes";
import { itemIsWorkspace } from "@/features/drivers/utils";
import { IconSize, UserRow } from "@gouvfr-lasuite/ui-kit";
import { formatSize } from "../../utils/utils";
import { WorkspaceShareModal } from "../modals/share/WorkspaceShareModal";

type ExplorerRightPanelContentProps = {
  item?: Item;
};

export const ExplorerRightPanelContent = ({
  item,
}: ExplorerRightPanelContentProps) => {
  const { setRightPanelOpen, selectedItems } = useGlobalExplorer();
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
        <div className="explorer__right-panel__section explorer__right-panel__section--info">
          <InfoRow
            label={t("explorer.rightPanel.format")}
            rightContent={t(getFormatTranslationKey(firstSelectedItem))}
          />
          <InfoRow
            label={t("explorer.rightPanel.updated_at")}
            rightContent={firstSelectedItem.updated_at.toLocaleString(
              undefined,
              {
                dateStyle: "short",
                timeStyle: "short",
              }
            )}
          />
          <InfoRow
            label={t("explorer.rightPanel.created_at")}
            rightContent={
              firstSelectedItem.created_at
                ? new Date(firstSelectedItem?.created_at).toLocaleString(
                    undefined,
                    {
                      dateStyle: "short",
                      timeStyle: "short",
                    }
                  )
                : ""
            }
          />
          {firstSelectedItem.size && (
            <InfoRow
              label={t("explorer.rightPanel.size")}
              rightContent={formatSize(firstSelectedItem.size)}
            />
          )}
          <InfoRow
            label={t("explorer.rightPanel.created_by")}
            rightContent={
              <UserRow fullName={firstSelectedItem.creator.full_name} />
            }
          />
        </div>
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
