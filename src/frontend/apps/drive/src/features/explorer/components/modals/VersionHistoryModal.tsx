import {
  Button,
  DropdownMenu,
  IconSize,
  Modal,
  ModalProps,
  ModalSize,
  useModals,
} from "@gouvfr-lasuite/ui-components";
import { useTranslation } from "react-i18next";
import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { Item, ItemVersion } from "@/features/drivers/types";
import { getDriver } from "@/features/config/Config";
import { useConfig } from "@/features/config/ConfigProvider";
import { useItemVersions } from "../../hooks/useQueries";
import { formatSize } from "@/features/explorer/utils/utils";
import {
  addToast,
  ToasterItem,
} from "@/features/ui/components/toaster/Toaster";
import { useRefreshItemCache } from "../../hooks/useRefreshItems";
import { useDownloadItem } from "@/features/items/hooks/useDownloadItem";
import { ItemIcon } from "../icons/ItemIcon";
import {
  Download,
  More,
  Restore,
  Trash,
  Upload,
} from "@gouvfr-lasuite/ui-components/icons";

type VersionHistoryModalProps = Pick<ModalProps, "isOpen" | "onClose"> & {
  item: Item;
};

type HistoryRow = {
  key: string;
  label: string;
  date: Date;
  size?: number;
  author?: string;
  onDownload: () => void;
  onRestore?: () => void;
  onDelete?: () => void;
};

const formatWhen = (date: Date) =>
  date.toLocaleString(undefined, {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });

const VersionHistoryRow = ({ row, item }: { row: HistoryRow; item: Item }) => {
  const { t } = useTranslation();
  const [isOpen, setIsOpen] = useState(false);
  const details = [
    formatWhen(row.date),
    typeof row.size === "number" ? formatSize(row.size, t) : undefined,
    row.author,
  ].filter((part): part is string => Boolean(part));

  const options = [
    {
      icon: <Download />,
      label: t("explorer.versions.modal.download"),
      value: "download",
      callback: () => {
        setIsOpen(false);
        row.onDownload();
      },
    },
    ...(row.onRestore
      ? [
          {
            icon: <Restore />,
            label: t("explorer.versions.modal.restore"),
            value: "restore",
            callback: () => {
              setIsOpen(false);
              row.onRestore?.();
            },
          },
        ]
      : []),
    ...(row.onDelete
      ? [
          {
            icon: <Trash />,
            label: t("explorer.versions.modal.delete"),
            value: "delete",
            callback: () => {
              setIsOpen(false);
              row.onDelete?.();
            },
          },
        ]
      : []),
  ];

  return (
    <li className="version-history__row">
      <span className="version-history__icon">
        <ItemIcon item={item} size={IconSize.MEDIUM} type="mini" />
      </span>
      <div className="version-history__meta">
        <span className="version-history__name">{row.label}</span>
        <span className="version-history__detail">{details.join(" · ")}</span>
      </div>
      <DropdownMenu
        options={options}
        isOpen={isOpen}
        onOpenChange={setIsOpen}
      >
        <Button
          variant="tertiary"
          size="small"
          aria-label={t("explorer.versions.modal.actions")}
          icon={<More />}
          onClick={() => setIsOpen(!isOpen)}
        />
      </DropdownMenu>
    </li>
  );
};

export const VersionHistoryModal = ({
  item,
  ...props
}: VersionHistoryModalProps) => {
  const { t } = useTranslation();
  const modals = useModals();
  const { config } = useConfig();
  const queryClient = useQueryClient();
  const refreshItemCache = useRefreshItemCache();
  const { handleDownloadItem } = useDownloadItem();
  const { data: versions, isLoading } = useItemVersions(item.id);
  const [liveItem, setLiveItem] = useState(item);
  const [importing, setImporting] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const abortRef = useRef<(() => Promise<void>) | null>(null);

  useEffect(() => {
    setLiveItem(item);
  }, [item]);

  useEffect(
    () => () => {
      void abortRef.current?.();
    },
    [],
  );

  const invalidate = () => {
    void queryClient.invalidateQueries({
      queryKey: ["itemVersions", item.id],
    });
    void refreshItemCache(item.id);
  };

  const refreshLiveItem = async () => {
    const refreshed = await getDriver().getItem(item.id);
    setLiveItem(refreshed);
    invalidate();
  };

  const handleClose = () => {
    void abortRef.current?.();
    props.onClose();
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
    await refreshLiveItem();
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

  const handleImport = async (file: File) => {
    setImporting(true);
    const uploadAcl =
      config?.AWS_S3_UPLOAD_ACL === "default"
        ? undefined
        : config?.AWS_S3_UPLOAD_ACL;
    const { promise, abort } = getDriver().replaceFile({
      itemId: item.id,
      file,
      uploadAcl,
    });
    abortRef.current = abort;
    try {
      const updated = await promise;
      abortRef.current = null;
      setLiveItem(updated);
      invalidate();
      addToast(
        <ToasterItem type="info">
          <span className="material-icons">history</span>
          <span>{t("explorer.versions.toast.imported")}</span>
        </ToasterItem>,
      );
    } catch {
      abortRef.current = null;
      addToast(
        <ToasterItem type="error">
          <span className="material-icons">error</span>
          <span>{t("explorer.versions.toast.import_error")}</span>
        </ToasterItem>,
      );
    } finally {
      setImporting(false);
    }
  };

  const canReplace = Boolean(liveItem.abilities?.versions_restore);
  const canDelete = Boolean(liveItem.abilities?.versions_destroy);
  const currentAuthor =
    liveItem.creator?.full_name || liveItem.creator?.short_name;

  const rows: HistoryRow[] = [
    {
      key: "current",
      label: t("explorer.versions.modal.current"),
      date: liveItem.updated_at,
      size: liveItem.size,
      author: currentAuthor,
      onDownload: () => {
        void handleDownloadItem(liveItem);
      },
    },
    ...(versions ?? []).map((version) => ({
      key: version.id,
      label: t("explorer.versions.modal.version", {
        n: version.version_number,
      }),
      date: version.created_at,
      size: version.size,
      author:
        version.created_by?.full_name || version.created_by?.short_name,
      onDownload: () => handleDownload(version),
      onRestore: canReplace
        ? () => {
            void handleRestore(version);
          }
        : undefined,
      onDelete: canDelete
        ? () => {
            void handleDelete(version);
          }
        : undefined,
    })),
  ];

  return (
    <Modal
      {...props}
      onClose={handleClose}
      size={ModalSize.MEDIUM}
      title={t("explorer.versions.modal.title")}
      subtitle={t("explorer.versions.modal.subtitle")}
      leftActions={
        canReplace ? (
          <Button
            variant="bordered"
            icon={<Upload />}
            disabled={importing}
            onClick={() => fileInputRef.current?.click()}
          >
            {importing
              ? t("explorer.versions.modal.importing")
              : t("explorer.versions.modal.import")}
          </Button>
        ) : undefined
      }
      rightActions={
        <Button onClick={handleClose}>
          {t("explorer.versions.modal.close")}
        </Button>
      }
    >
      <input
        ref={fileInputRef}
        type="file"
        hidden
        onChange={(event) => {
          const file = event.target.files?.[0];
          event.target.value = "";
          if (file) {
            void handleImport(file);
          }
        }}
      />
      {isLoading && <p>{t("explorer.versions.modal.loading")}</p>}
      {!isLoading && (
        <ul className="version-history">
          {rows.map((row) => (
            <VersionHistoryRow key={row.key} row={row} item={liveItem} />
          ))}
        </ul>
      )}
    </Modal>
  );
};
