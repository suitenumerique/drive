import { ToasterItem } from "@/features/ui/components/toaster/Toaster";
import { Button, Tooltip } from "@gouvfr-lasuite/cunningham-react";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import clsx from "clsx";
import { CircularProgress } from "@/features/ui/components/circular-progress/CircularProgress";
import prettyBytes from "pretty-bytes";
import { ToastContentProps } from "react-toastify";
import { getIconByMimeType } from "../icons/ItemIcon";
import { UploadingState } from "@/features/explorer/hooks/useUpload";
import { Spinner } from "@gouvfr-lasuite/ui-kit";
import { FileUploadMeta } from "@/features/explorer/components/app-view/AppExplorerInner";
import { CancelUploadConfirmationModal } from "@/features/explorer/components/modals/CancelUploadConfirmationModal";
import { ErrorIcon } from "@/features/ui/components/icon/ErrorIcon";

const CheckIcon = () => (
  <span className="material-icons file-upload-toast__files__item__check">
    check_circle
  </span>
);

const FileErrorIcon = () => (
  <div className="file-upload-toast__files__item__error-icon">
    <ErrorIcon size={20} />
  </div>
);

const FileRow = ({
  name,
  meta,
  onCancelFile,
}: {
  name: string;
  meta: FileUploadMeta;
  onCancelFile?: (name: string) => void;
}) => {
  const { t } = useTranslation();
  const icon = getIconByMimeType(meta.file.type, "normal");
  const [hovered, setHovered] = useState(false);

  if (meta.status === "cancelled") {
    return null;
  }

  return (
    <div
      className={clsx("file-upload-toast__files__item", {
        "file-upload-toast__files__item--error": meta.status === "error",
      })}
    >
      <div className="file-upload-toast__files__item__name">
        <img src={icon.src} alt={name} />
        <span>{name}</span>
        {meta.status !== "error" && (
          <span className="file-upload-toast__files__item__size">
            {prettyBytes(meta.file.size)}
          </span>
        )}
      </div>
      <div className="file-upload-toast__files__item__progress">
        {meta.status === "done" && <CheckIcon />}
        {meta.status === "error" && (
          <Tooltip
            content={t(
              `explorer.actions.upload.files.error_reasons.${meta.error ?? "unknown"}`,
            )}
          >
            <div className="file-upload-toast__files__item__progress">
              <span className="file-upload-toast__files__item__error-text">
                {t(`explorer.actions.upload.files.error_short.${meta.error ?? "unknown"}`, t("explorer.actions.upload.files.error"))}
              </span>
              <FileErrorIcon />
            </div>
          </Tooltip>
        )}
        {meta.status === "uploading" && (
          <div
            className="file-upload-toast__files__item__progress--hoverable"
            onMouseEnter={() => setHovered(true)}
            onMouseLeave={() => setHovered(false)}
            onClick={() => onCancelFile?.(name)}
          >
            <CircularProgress progress={meta.progress} />
            {hovered && (
              <div className="file-upload-toast__files__item__cancel-overlay">
                <span className="material-icons file-upload-toast__files__item__cancel-icon">
                  close
                </span>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

/**
 * Sort files: uploading first, done second, errors/cancelled at the bottom.
 */
const sortEntries = (
  entries: [string, FileUploadMeta][],
): [string, FileUploadMeta][] => {
  const order: Record<string, number> = {
    uploading: 0,
    done: 1,
    cancelled: 2,
    error: 3,
  };
  return [...entries].sort(
    (a, b) => (order[a[1].status] ?? 9) - (order[b[1].status] ?? 9),
  );
};

export const FileUploadToast = (
  props: {
    uploadingState: UploadingState;
    onCancelFile?: (fileName: string) => void;
    onCancelAll?: () => void;
  } & Partial<ToastContentProps>,
) => {
  const { t } = useTranslation();
  const [isOpen, setIsOpen] = useState(true);
  const [isCancelModalOpen, setIsCancelModalOpen] = useState(false);

  const allFiles = Object.values(props.uploadingState.filesMeta);
  const activeFiles = allFiles.filter((m) => m.status !== "cancelled");
  const uploadingFiles = allFiles.filter((m) => m.status === "uploading");
  const doneFiles = allFiles.filter((m) => m.status === "done");
  const errorFiles = allFiles.filter((m) => m.status === "error");
  const pendingFilesCount = uploadingFiles.length;
  const doneFilesCount = doneFiles.length;
  const errorCount = errorFiles.length;

  // Overall progress percentage
  const overallProgress =
    activeFiles.length > 0
      ? Math.floor(
          activeFiles.reduce((sum, m) => sum + m.progress, 0) /
            activeFiles.length,
        )
      : 0;

  // Does not show the files list and the open button.
  const simpleMode =
    props.uploadingState.step === "preparing" ||
    props.uploadingState.step === "create_folders";

  const isDone =
    pendingFilesCount === 0 && props.uploadingState.step === "done";
  const canClose = pendingFilesCount === 0;

  useEffect(() => {
    if (props.uploadingState.step === "upload_files") {
      setIsOpen(true);
    }
  }, [props.uploadingState.step]);

  useEffect(() => {
    if (pendingFilesCount === 0 && errorCount === 0) {
      setIsOpen(false);
    } else if (pendingFilesCount === 0 && errorCount > 0) {
      setIsOpen(true);
    }
  }, [pendingFilesCount, errorCount]);

  const sortedEntries = sortEntries(
    Object.entries(props.uploadingState.filesMeta),
  );

  return (
    <ToasterItem className="file-upload-toast__item">
      <div className="file-upload-toast">
        <div
          className={clsx("file-upload-toast__files", {
            "file-upload-toast__files--closed": !isOpen,
          })}
        >
          {sortedEntries.map(([name, meta]) => (
            <FileRow
              key={name}
              name={name}
              meta={meta}
              onCancelFile={props.onCancelFile}
            />
          ))}
        </div>
        <div className="file-upload-toast__description">
          <div className="file-upload-toast__description__text">
            {simpleMode ? (
              <>
                <Spinner />
                {t(
                  `explorer.actions.upload.steps.${props.uploadingState.step}`,
                )}
              </>
            ) : (
              <>
                {pendingFilesCount > 0 ? (
                  <>
                    {t("explorer.actions.upload.files.description", {
                      count: pendingFilesCount,
                    })}
                    <span className="file-upload-toast__description__percentage">
                      {overallProgress}%
                    </span>
                  </>
                ) : isDone && doneFilesCount > 0 ? (
                  t("explorer.actions.upload.files.description_done", {
                    count: doneFilesCount,
                  })
                ) : null}
                {errorCount > 0 && (
                  <Tooltip
                    content={t("explorer.actions.upload.files.error_count", {
                      count: errorCount,
                    })}
                  >
                    <span className="file-upload-toast__description__error-indicator">
                      <ErrorIcon size={20} />
                    </span>
                  </Tooltip>
                )}
              </>
            )}
          </div>
          <div>
            {!simpleMode && (
              <Button
                variant="tertiary"
                size="small"
                icon={
                  <span className="material-icons">
                    {isOpen ? "keyboard_arrow_up" : "keyboard_arrow_down"}
                  </span>
                }
                onClick={() => setIsOpen(!isOpen)}
              ></Button>
            )}

            {canClose ? (
              <Button
                onClick={props.closeToast}
                variant="tertiary"
                size="small"
                icon={<span className="material-icons">close</span>}
              ></Button>
            ) : (
              <Button
                onClick={() => setIsCancelModalOpen(true)}
                variant="tertiary"
                size="small"
                icon={<span className="material-icons">close</span>}
              ></Button>
            )}
          </div>
        </div>
      </div>
      <CancelUploadConfirmationModal
        isOpen={isCancelModalOpen}
        onClose={() => setIsCancelModalOpen(false)}
        onConfirm={() => {
          props.onCancelAll?.();
          props.closeToast?.();
        }}
      />
    </ToasterItem>
  );
};
