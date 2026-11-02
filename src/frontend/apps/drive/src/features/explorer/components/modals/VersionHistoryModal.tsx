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
      {isLoading && <p className="mb-s">{t("explorer.versions.modal.loading")}</p>}
      {!isLoading && (!versions || versions.length === 0) && (
        <p className="mb-s">{t("explorer.versions.modal.empty")}</p>
      )}
      {!isLoading &&
        versions?.map((version) => (
          <div
            key={version.id}
            className="d-flex align-center justify-space-between p-s"
            style={{ borderBottom: "1px solid var(--c--theme--colors--greyscale-200)" }}
          >
            <div>
              <p className="mb-0">
                <strong>{t("explorer.versions.modal.version", { n: version.version_number })}</strong>
              </p>
              <p className="mb-0" style={{ color: "var(--c--theme--colors--greyscale-500)" }}>
                {version.created_at.toLocaleString()}
              </p>
              {typeof version.size === "number" && (
                <p className="mb-0" style={{ color: "var(--c--theme--colors--greyscale-500)" }}>
                  {formatSize(version.size, t)}
                </p>
              )}
            </div>
            <div className="d-flex">
              <Button
                variant="quaternary"
                size="small"
                onClick={() => handleDownload(version)}
              >
                <Download />
              </Button>
              {hasRestore && (
                <Button
                  variant="quaternary"
                  size="small"
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
                  onClick={() => {
                    void handleDelete(version);
                  }}
                >
                  <Trash />
                </Button>
              )}
            </div>
          </div>
        ))}
    </Modal>
  );
};
