import {
  Button,
  Modal,
  ModalProps,
  ModalSize,
  useModals,
} from "@gouvfr-lasuite/ui-components";
import { useTranslation } from "react-i18next";
import { useQueryClient } from "@tanstack/react-query";
import { Item, ItemVersion } from "@/features/drivers/types";
import { getDriver } from "@/features/config/Config";
import { useItemVersions } from "../../hooks/useQueries";
import { formatSize } from "@/features/explorer/utils/utils";
import {
  addToast,
  ToasterItem,
} from "@/features/ui/components/toaster/Toaster";
import { useRefreshItemCache } from "../../hooks/useRefreshItems";
import { Download, Restore, Trash } from "@gouvfr-lasuite/ui-components/icons";

type VersionHistoryModalProps = Pick<ModalProps, "isOpen" | "onClose"> & {
  item: Item;
};

export const VersionHistoryModal = ({
  item,
  ...props
}: VersionHistoryModalProps) => {
  const { t } = useTranslation();
  const modals = useModals();
  const queryClient = useQueryClient();
  const refreshItemCache = useRefreshItemCache();
  const { data: versions, isLoading } = useItemVersions(item.id);

  const invalidate = () => {
    void queryClient.invalidateQueries({
      queryKey: ["itemVersions", item.id],
    });
    void refreshItemCache(item.id);
  };

  const handleDownload = (version: ItemVersion) => {
    void getDriver().downloadItemVersion(item.id, version.id);
  };

  const handleRestore = async (version: ItemVersion) => {
    const decision = await modals.confirmationModal({
      size: ModalSize.MEDIUM,
      title: t("explorer.versions.confirm_restore.title"),
      children: t("explorer.versions.confirm_restore.description"),
    });
    if (decision !== "yes") {
      return;
    }
    await getDriver().restoreItemVersion(item.id, version.id);
    invalidate();
    addToast(
      <ToasterItem type="info">
        <span className="material-icons">history</span>
        <span>{t("explorer.versions.toast.restored")}</span>
      </ToasterItem>,
    );
  };

  const handleDelete = async (version: ItemVersion) => {
    const decision = await modals.confirmationModal({
      size: ModalSize.MEDIUM,
      title: t("explorer.versions.confirm_delete.title"),
      children: t("explorer.versions.confirm_delete.description"),
    });
    if (decision !== "yes") {
      return;
    }
    await getDriver().deleteItemVersion(item.id, version.id);
    invalidate();
    addToast(
      <ToasterItem type="info">
        <span className="material-icons">history</span>
        <span>{t("explorer.versions.toast.deleted")}</span>
      </ToasterItem>,
    );
  };

  const hasRestore = item.abilities?.versions_restore;
  const hasDelete = item.abilities?.versions_destroy;

  return (
    <Modal
      {...props}
      size={ModalSize.MEDIUM}
      title={t("explorer.versions.modal.title")}
      rightActions={
        <Button variant="bordered" onClick={props.onClose}>
          {t("explorer.actions.rename.modal.cancel")}
        </Button>
      }
    >
      {isLoading && <p>{t("explorer.versions.modal.loading")}</p>}
      {!isLoading && (!versions || versions.length === 0) && (
        <p>{t("explorer.versions.modal.empty")}</p>
      )}
      {!isLoading && versions && versions.length > 0 && (
        <ul className="version-history">
          {versions.map((version) => {
            const author =
              version.created_by?.full_name || version.created_by?.short_name;
            return (
              <li key={version.id} className="version-history__row">
                <div className="version-history__meta">
                  <span className="version-history__name">
                    {t("explorer.versions.modal.version", {
                      n: version.version_number,
                    })}
                  </span>
                  <span className="version-history__detail">
                    {version.created_at.toLocaleString()}
                  </span>
                  {typeof version.size === "number" && (
                    <span className="version-history__detail">
                      {formatSize(version.size, t)}
                    </span>
                  )}
                  {author && (
                    <span className="version-history__detail">{author}</span>
                  )}
                </div>
                <div className="version-history__actions">
                  <Button
                    variant="quaternary"
                    size="small"
                    aria-label={t("explorer.versions.modal.download")}
                    onClick={() => handleDownload(version)}
                  >
                    <Download />
                  </Button>
                  {hasRestore && (
                    <Button
                      variant="quaternary"
                      size="small"
                      aria-label={t("explorer.versions.modal.restore")}
                      onClick={() => {
                        void handleRestore(version);
                      }}
                    >
                      <Restore />
                    </Button>
                  )}
                  {hasDelete && (
                    <Button
                      variant="quaternary"
                      size="small"
                      aria-label={t("explorer.versions.modal.delete")}
                      onClick={() => {
                        void handleDelete(version);
                      }}
                    >
                      <Trash />
                    </Button>
                  )}
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </Modal>
  );
};
