import { ToasterItem } from "@/features/ui/components/toaster/Toaster";
import { Button, Tooltip } from "@gouvfr-lasuite/cunningham-react";
import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import clsx from "clsx";
import { CircularProgress } from "@/features/ui/components/circular-progress/CircularProgress";
import prettyBytes from "pretty-bytes";
import { ToastContentProps } from "react-toastify";
import { getIconByMimeType } from "../icons/ItemIcon";
import {
  UploadingState,
  UploadingStep,
  FileUploadMeta,
  FileUploadStatus,
} from "@/features/explorer/hooks/useUpload";
import { Spinner } from "@gouvfr-lasuite/ui-kit";
import { CancelUploadConfirmationModal } from "@/features/explorer/components/modals/CancelUploadConfirmationModal";
import { ErrorIcon } from "@/features/ui/components/icon/ErrorIcon";
import { CheckIcon } from "@/features/ui/components/icon/CheckIcon";

const FileErrorIcon = () => (
  <div className="file-upload-toast__files__item__error-icon">
    <ErrorIcon size={20} />
  </div>
);

export const FileRow = ({
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

  return (
    <div
      className={clsx("file-upload-toast__files__item", {
        "file-upload-toast__files__item--error":
          meta.status === FileUploadStatus.ERROR,
      })}
    >
      <div className="file-upload-toast__files__item__name">
        <img src={icon.src} alt={name} />
        <span>{name}</span>
        {meta.status !== FileUploadStatus.ERROR && (
          <span className="file-upload-toast__files__item__size">
            {prettyBytes(meta.file.size)}
          </span>
        )}
      </div>
      <div className="file-upload-toast__files__item__progress">
        {meta.status === FileUploadStatus.DONE && (
          <div className="file-upload-toast__files__item__check">
            <CheckIcon />
          </div>
        )}
        {meta.status === FileUploadStatus.ERROR && (
          <Tooltip
            content={t(
              `explorer.actions.upload.files.error_reasons.${meta.error ?? "unknown"}`,
            )}
          >
            <div className="file-upload-toast__files__item__progress">
              <span className="file-upload-toast__files__item__error-text">
                {t(
                  `explorer.actions.upload.files.error_short.${meta.error ?? "unknown"}`,
                  t("explorer.actions.upload.files.error"),
                )}
              </span>
              <FileErrorIcon />
            </div>
          </Tooltip>
        )}
        {meta.status === FileUploadStatus.UPLOADING && (
          <div
            role="button"
            tabIndex={0}
            className="file-upload-toast__files__item__progress--hoverable"
            onMouseEnter={() => setHovered(true)}
            onMouseLeave={() => setHovered(false)}
            onClick={() => onCancelFile?.(name)}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                onCancelFile?.(name);
              }
            }}
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
    [FileUploadStatus.UPLOADING]: 0,
    [FileUploadStatus.DONE]: 0,
    [FileUploadStatus.CANCELLED]: 1,
    [FileUploadStatus.ERROR]: 2,
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

  const { activeFiles, uploadingFiles, doneFiles, errorFiles } = useMemo(() => {
    const allFiles = Object.values(props.uploadingState.filesMeta);
    return {
      activeFiles: allFiles.filter(
        (m) => m.status !== FileUploadStatus.CANCELLED,
      ),
      uploadingFiles: allFiles.filter(
        (m) => m.status === FileUploadStatus.UPLOADING,
      ),
      doneFiles: allFiles.filter((m) => m.status === FileUploadStatus.DONE),
      errorFiles: allFiles.filter((m) => m.status === FileUploadStatus.ERROR),
    };
  }, [props.uploadingState.filesMeta]);
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
    props.uploadingState.step === UploadingStep.PREPARING ||
    props.uploadingState.step === UploadingStep.CREATE_FOLDERS;

  const isDone =
    pendingFilesCount === 0 && props.uploadingState.step === UploadingStep.DONE;
  const canClose = pendingFilesCount === 0;

  useEffect(() => {
    if (props.uploadingState.step === UploadingStep.UPLOAD_FILES) {
      setIsOpen(true);
    }
  }, [props.uploadingState.step]);

  useEffect(() => {
    if (pendingFilesCount === 0) {
      if (errorCount === 0) {
        setIsOpen(false);
      } else {
        setIsOpen(true);
      }
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
          {sortedEntries
            .filter(([, meta]) => meta.status !== FileUploadStatus.CANCELLED)
            .map(([name, meta]) => (
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
                ) : isDone && doneFilesCount === 0 && errorCount > 0 ? (
                  t("explorer.actions.upload.files.error_count", {
                    count: errorCount,
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
          <div className="file-upload-toast__description__actions">
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
