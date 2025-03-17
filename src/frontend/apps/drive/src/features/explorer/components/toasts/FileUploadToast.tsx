import { ToasterItem } from "@/features/ui/components/toaster/Toaster";
import { Button } from "@openfun/cunningham-react";
import { useEffect, useState } from "react";
import { FileUploadMeta } from "../ExplorerInner";
import { useTranslation } from "react-i18next";
import clsx from "clsx";
import { CircularProgress } from "@/features/ui/components/circular-progress/CircularProgress";
import prettyBytes from "pretty-bytes";
import { ToastContentProps } from "react-toastify";

export const FileUploadToast = (
  props: {
    uploadingState: Record<string, FileUploadMeta>;
  } & Partial<ToastContentProps>
) => {
  const { t } = useTranslation();
  const [isOpen, setIsOpen] = useState(true);
  const pendingFilesCount = Object.values(props.uploadingState).filter(
    (meta) => meta.progress < 100
  ).length;
  const doneFilesCount = Object.values(props.uploadingState).filter(
    (meta) => meta.progress >= 100
  ).length;

  useEffect(() => {
    if (pendingFilesCount === 0) {
      setIsOpen(false);
    } else {
      setIsOpen(true);
    }
  }, [pendingFilesCount]);

  return (
    <ToasterItem className="file-upload-toast__item">
      <div className="file-upload-toast">
        <div
          className={clsx("file-upload-toast__files", {
            "file-upload-toast__files--closed": !isOpen,
          })}
        >
          {Object.entries(props.uploadingState)
            .reverse()
            .map(([name, meta]) => (
              <div key={name} className="file-upload-toast__files__item">
                <div className="file-upload-toast__files__item__name">
                  <span>{name}</span>
                  <span className="file-upload-toast__files__item__size">
                    {prettyBytes(meta.file.size)}
                  </span>
                </div>
                <div className="file-upload-toast__files__item__progress">
                  <CircularProgress progress={meta.progress} />
                </div>
              </div>
            ))}
        </div>
        <div className="file-upload-toast__description">
          <div>
            {pendingFilesCount > 0
              ? t("explorer.actions.upload.files.description", {
                  count: pendingFilesCount,
                })
              : doneFilesCount > 0
              ? t("explorer.actions.upload.files.description_done", {
                  count: doneFilesCount,
                })
              : null}
          </div>
          <div>
            <Button
              color="primary-text"
              size="small"
              icon={
                <span className="material-icons">
                  {isOpen ? "keyboard_arrow_up" : "keyboard_arrow_down"}
                </span>
              }
              onClick={() => setIsOpen(!isOpen)}
            ></Button>
            <Button
              onClick={props.closeToast}
              disabled={pendingFilesCount > 0}
              color="primary-text"
              size="small"
              icon={<span className="material-icons">close</span>}
            ></Button>
          </div>
        </div>
      </div>
    </ToasterItem>
  );
};
