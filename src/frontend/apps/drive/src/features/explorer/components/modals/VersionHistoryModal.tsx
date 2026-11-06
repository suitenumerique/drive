import {
  Button,
  DropdownMenu,
  IconSize,
  Modal,
  ModalProps,
  ModalSize,
} from "@gouvfr-lasuite/ui-components";
import { useTranslation } from "react-i18next";
import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { Item, ItemVersion } from "@/features/drivers/types";
import { getDriver } from "@/features/config/Config";
import { useConfig } from "@/features/config/ConfigProvider";
import { useItemVersions } from "../../hooks/useQueries";
import {
  addToast,
  ToasterItem,
} from "@/features/ui/components/toaster/Toaster";
import { useRefreshItemCache } from "../../hooks/useRefreshItems";
import { useDownloadItem } from "@/features/items/hooks/useDownloadItem";
import { ItemIcon } from "../icons/ItemIcon";
import {
  ArrowUpRight,
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
  filename: string;
  date: Date;
  author?: string;
  onPreview?: () => void;
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
  const detail = [formatWhen(row.date), row.author]
    .filter((part): part is string => Boolean(part))
    .join(" • ");

  const options = [
    ...(row.onPreview
      ? [
          {
            icon: <ArrowUpRight />,
            label: t("explorer.versions.modal.preview"),
            value: "preview",
            callback: () => {
              setIsOpen(false);
              row.onPreview?.();
            },
          },
        ]
      : []),
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
          { type: "separator" as const },
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
        <span className="version-history__file">{row.filename}</span>
        <span className="version-history__detail">{detail}</span>
      </div>
      <DropdownMenu options={options} isOpen={isOpen} onOpenChange={setIsOpen}>
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
  const { config } = useConfig();
  const queryClient = useQueryClient();
  const refreshItemCache = useRefreshItemCache();
  const { handleDownloadItem } = useDownloadItem();
  const { data: versions, isLoading } = useItemVersions(item.id);
  const [liveItem, setLiveItem] = useState(item);
  const [importing, setImporting] = useState(false);
  const [pending, setPending] = useState<
    | { kind: "restore"; version: ItemVersion }
    | { kind: "delete"; version: ItemVersion }
    | { kind: "delete-current"; nextNumber: number }
    | null
  >(null);
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

  const confirmPending = async () => {
    if (!pending) {
      return;
    }
    const action = pending;
    setPending(null);
    if (action.kind === "restore") {
      await getDriver().restoreItemVersion(item.id, action.version.id);
      await refreshLiveItem();
      addToast(
        <ToasterItem type="info">
          <span className="material-icons">history</span>
          <span>{t("explorer.versions.toast.restored")}</span>
        </ToasterItem>,
      );
      return;
    }
    if (action.kind === "delete") {
      await getDriver().deleteItemVersion(item.id, action.version.id);
      invalidate();
      addToast(
        <ToasterItem type="info">
          <span className="material-icons">history</span>
          <span>{t("explorer.versions.toast.deleted")}</span>
        </ToasterItem>,
      );
      return;
    }
    await getDriver().discardCurrentVersion(item.id);
    await refreshLiveItem();
    addToast(
      <ToasterItem type="info">
        <span className="material-icons">history</span>
        <span>{t("explorer.versions.toast.deleted_current")}</span>
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

  const newest = versions?.[0];
  const rows: HistoryRow[] = [
    {
      key: "current",
      label: t("explorer.versions.modal.current"),
      filename: liveItem.filename || liveItem.title,
      date: liveItem.updated_at,
      author: currentAuthor,
      onPreview: () => {
        window.open(
          `/explorer/items/files/${liveItem.id}`,
          "_blank",
          "noopener,noreferrer",
        );
      },
      onDownload: () => {
        void handleDownloadItem(liveItem);
      },
      onDelete:
        canDelete && newest
          ? () =>
              setPending({
                kind: "delete-current",
                nextNumber: newest.version_number,
              })
          : undefined,
    },
    ...(versions ?? []).map((version) => ({
      key: version.id,
      label: t("explorer.versions.modal.version", {
        n: version.version_number,
      }),
      filename: version.filename,
      date: version.created_at,
      author: version.created_by?.full_name || version.created_by?.short_name,
      onDownload: () => handleDownload(version),
      onRestore: canReplace
        ? () => setPending({ kind: "restore", version })
        : undefined,
      onDelete: canDelete
        ? () => setPending({ kind: "delete", version })
        : undefined,
    })),
  ];

  const confirmTitle =
    pending?.kind === "restore"
      ? t("explorer.versions.confirm_restore.title", {
          n: pending.version.version_number,
        })
      : pending?.kind === "delete"
        ? t("explorer.versions.confirm_delete.title", {
            n: pending.version.version_number,
          })
        : pending?.kind === "delete-current"
          ? t("explorer.versions.confirm_delete_current.title")
          : "";
  const confirmDescription =
    pending?.kind === "restore"
      ? t("explorer.versions.confirm_restore.description", {
          n: pending.version.version_number,
        })
      : pending?.kind === "delete"
        ? t("explorer.versions.confirm_delete.description", {
            n: pending.version.version_number,
          })
        : pending?.kind === "delete-current"
          ? t("explorer.versions.confirm_delete_current.description", {
              n: pending.nextNumber,
            })
          : "";
  const confirmLabel =
    pending?.kind === "restore"
      ? t("explorer.versions.modal.restore")
      : t("explorer.versions.modal.delete");

  return (
    <>
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
    {pending && (
      <Modal
        isOpen
        onClose={() => setPending(null)}
        size={ModalSize.SMALL}
        title={confirmTitle}
      >
        <p className="version-confirm__text">{confirmDescription}</p>
        <div className="version-confirm__actions">
          <Button
            fullWidth
            color={pending.kind === "restore" ? undefined : "error"}
            onClick={() => {
              void confirmPending();
            }}
          >
            {confirmLabel}
          </Button>
          <Button
            fullWidth
            variant="bordered"
            onClick={() => setPending(null)}
          >
            {t("explorer.versions.modal.cancel")}
          </Button>
        </div>
      </Modal>
    )}
    </>
  );
};
