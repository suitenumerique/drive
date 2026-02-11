import { ToasterItem } from "@/features/ui/components/toaster/Toaster";
import { Button } from "@gouvfr-lasuite/cunningham-react";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import clsx from "clsx";
import { CircularProgress } from "@/features/ui/components/circular-progress/CircularProgress";
import prettyBytes from "pretty-bytes";
import { ToastContentProps } from "react-toastify";
import { getIconByMimeType } from "../icons/ItemIcon";
import { UploadingState } from "@/features/explorer/hooks/useUpload";
import { Spinner } from "@gouvfr-lasuite/ui-kit";
import { useConfig } from "@/features/config/ConfigProvider";
import { getOperationTimeBound } from "@/features/operations/timeBounds";
import { useTimeBoundedPhase } from "@/features/operations/useTimeBoundedPhase";
import { useMemo } from "react";

export const FileUploadToast = (
  props: {
    uploadingState: UploadingState;
    onRetry?: (path: string) => void;
  } & Partial<ToastContentProps>
) => {
  const { t } = useTranslation();
  const { config } = useConfig();
  const [isOpen, setIsOpen] = useState(true);
  const metas = Object.values(props.uploadingState.filesMeta);
  const inProgressFilesCount = metas.filter(
    (meta) => meta.status !== "failed" && meta.progress < 100,
  ).length;
  const doneFilesCount = metas.filter(
    (meta) => meta.status !== "failed" && meta.progress >= 100,
  ).length;
  const failedFilesCount = metas.filter((meta) => meta.status === "failed").length;
  // Does not show the files list and the open button.
  const simpleMode =
    props.uploadingState.step === "preparing" ||
    props.uploadingState.step === "create_folders";

  const simpleModeBounds = useMemo(
    () => getOperationTimeBound("upload_create", config),
    [config],
  );
  const simpleModePhase = useTimeBoundedPhase(simpleMode, simpleModeBounds);

  useEffect(() => {
    if (props.uploadingState.step === "upload_files") {
      setIsOpen(true);
    }
  }, [props.uploadingState.step]);

  useEffect(() => {
    if (inProgressFilesCount === 0) {
      setIsOpen(false);
    }
  }, [inProgressFilesCount]);

  return (
    <ToasterItem className="file-upload-toast__item">
      <div className="file-upload-toast">
        <div
          className={clsx("file-upload-toast__files", {
            "file-upload-toast__files--closed": !isOpen,
          })}
        >
          {Object.entries(props.uploadingState.filesMeta).map(
            ([name, meta]) => {
              const icon = getIconByMimeType(meta.file.type, "normal");
              return (
                <div key={name} className="file-upload-toast__files__item">
                  <div className="file-upload-toast__files__item__name">
                    <img src={icon.src} alt={name} />
                    <span>{name}</span>
                    <span className="file-upload-toast__files__item__size">
                      {prettyBytes(meta.file.size)}
                    </span>
                  </div>
                  <div className="file-upload-toast__files__item__progress">
                    {meta.status === "failed" ? (
                      <Button
                        variant="secondary"
                        size="small"
                        onClick={() => props.onRetry?.(name)}
                      >
                        {t(
                          `explorer.actions.upload.actions.${meta.error?.nextAction ?? "retry"}`,
                        )}
                      </Button>
                    ) : (
                      <CircularProgress progress={meta.progress} />
                    )}
                  </div>
                </div>
              );
            }
          )}
        </div>
        <div className="file-upload-toast__description">
          <div className="file-upload-toast__description__text">
            {simpleMode ? (
              <>
                <Spinner />
                {t(
                  `explorer.actions.upload.steps.${props.uploadingState.step}`
                )}
                {simpleModePhase === "still_working" && (
                  <span> {t("operations.long_running.still_working")}</span>
                )}
                {simpleModePhase === "failed" && (
                  <span> {t("operations.long_running.failed")}</span>
                )}
              </>
            ) : (
              <>
                {inProgressFilesCount > 0
                  ? t("explorer.actions.upload.files.description", {
                      count: inProgressFilesCount,
                    })
                  : failedFilesCount > 0
                    ? t("explorer.actions.upload.files.description_failed", {
                        count: failedFilesCount,
                      })
                    : doneFilesCount > 0
                      ? t("explorer.actions.upload.files.description_done", {
                          count: doneFilesCount,
                        })
                      : null}
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

            <Button
              onClick={props.closeToast}
              disabled={inProgressFilesCount > 0}
              variant="tertiary"
              size="small"
              icon={<span className="material-icons">close</span>}
            ></Button>
          </div>
        </div>
      </div>
    </ToasterItem>
  );
};
