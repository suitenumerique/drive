import {
  Button,
  FileIcon,
  FilePreviewType,
  Icon,
  IconSize,
  IconType,
  Modal,
  ModalSize,
  removeFileExtension,
} from "@gouvfr-lasuite/ui-components";
import clsx from "clsx";
import { ReactNode, useEffect, useState } from "react";
import { getEffectiveMimetype } from "@/features/explorer/utils/mimeTypes";
import {
  EncryptedFileViewer,
  EncryptedPreviewFile,
} from "./EncryptedFileViewer";

type EncryptedFilesPreviewProps = {
  isOpen: boolean;
  onClose?: () => void;
  files: EncryptedPreviewFile[];
  openedFileId?: string;
  customHeaderActions?: (headerActions: ReactNode) => ReactNode;
  sidebarContent?: ReactNode;
  onChangeFile?: (file?: FilePreviewType) => void;
  onFileOpen?: (file: FilePreviewType) => void;
  handleDownloadFile?: (file?: FilePreviewType) => void;
};

// Viewers that hold unsaved work (the encrypted office editor) register this
// guard; it must resolve before the viewer is unmounted, or the editor's
// iframe is gone by the time its save runs.
const flushSaveGuardThen = async (next: () => void) => {
  const guard = (
    window as unknown as { __driveOOEditorSaveGuard?: () => Promise<void> }
  ).__driveOOEditorSaveGuard;
  if (guard) {
    try {
      await guard();
    } catch (e) {
      console.error("[EncryptedFilesPreview] save guard threw", e);
    }
  }
  next();
};

/**
 * Full-screen preview shown while the current file is encrypted.
 *
 * The design system's `FilePreview` picks its viewer from the mimetype and
 * loads `url_preview` itself, with no slot for another viewer: an encrypted
 * file needs decrypting first (or the in-browser office editor). This shell
 * reproduces its markup, so it inherits the same styles, and renders
 * `EncryptedFileViewer` instead. It walks the same file list: moving onto a
 * plain file reports it through `onChangeFile`, and the caller switches back
 * to the design system's preview.
 */
export const EncryptedFilesPreview = ({
  isOpen,
  onClose,
  files,
  openedFileId,
  customHeaderActions,
  sidebarContent,
  onChangeFile,
  onFileOpen,
  handleDownloadFile,
}: EncryptedFilesPreviewProps) => {
  const [currentIndex, setCurrentIndex] = useState(() =>
    files.findIndex((file) => file.id === openedFileId),
  );
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  useEffect(() => {
    setCurrentIndex(files.findIndex((file) => file.id === openedFileId));
  }, [openedFileId, files]);

  const currentFile = currentIndex > -1 ? files[currentIndex] : undefined;
  const hasNext = currentIndex < files.length - 1;
  const hasPrevious = currentIndex > 0;

  const goTo = (index: number) =>
    flushSaveGuardThen(() => setCurrentIndex(index));
  const goNext = () => hasNext && goTo(currentIndex + 1);
  const goPrevious = () => hasPrevious && goTo(currentIndex - 1);
  const close = () => flushSaveGuardThen(() => onClose?.());

  const handleDownload = () => handleDownloadFile?.(currentFile);

  useEffect(() => {
    onChangeFile?.(currentFile);
    if (currentFile) {
      onFileOpen?.(currentFile);
    }
    // Only a change of file is reported, like the design system's preview.
     
  }, [currentFile]);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      const tag = (event.target as HTMLElement | null)?.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") {
        return;
      }
      if (event.key === "ArrowLeft") {
        event.preventDefault();
        goPrevious();
      } else if (event.key === "ArrowRight") {
        event.preventDefault();
        goNext();
      }
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
     
  }, [currentIndex, files.length]);

  useEffect(() => {
    if (!isOpen || !currentFile) {
      return;
    }
    const previousTitle = document.title;
    document.title = currentFile.title;
    return () => {
      document.title = previousTitle;
    };
  }, [isOpen, currentFile]);

  const headerActions = (
    <>
      {handleDownloadFile && (
        <Button
          variant="tertiary"
          onClick={handleDownload}
          icon={<Icon type={IconType.OUTLINED} name="file_download" />}
        />
      )}
      <Button
        variant="tertiary"
        onClick={() => setIsSidebarOpen((open) => !open)}
        icon={<Icon name="info_outline" />}
      />
    </>
  );

  if (!isOpen || !currentFile) {
    return null;
  }

  return (
    <Modal
      isOpen={isOpen}
      onClose={close}
      size={ModalSize.FULL}
      hideCloseButton
    >
      <div data-testid="file-preview">
        <div
          onClick={(event) => {
            const target = event.target;
            if (
              target instanceof HTMLElement &&
              (target === event.currentTarget ||
                target.dataset.previewBackdrop === "true")
            ) {
              close();
            }
          }}
          className={clsx(
            "file-preview__container",
            isSidebarOpen && "file-preview__container--sidebar-open",
          )}
        >
          <div className="file-preview__header">
            <div className="file-preview__header__content">
              <div className="file-preview__header__content__left">
                <Button
                  variant="tertiary"
                  size="small"
                  onClick={close}
                  icon={<Icon name="close" />}
                />
                <div className="file-preview__title-wrapper">
                  <FileIcon
                    file={{
                      ...currentFile,
                      // Encrypted uploads are stored as octet-stream.
                      mimetype:
                        getEffectiveMimetype(
                          currentFile as unknown as Parameters<
                            typeof getEffectiveMimetype
                          >[0],
                        ) ?? currentFile.mimetype,
                    }}
                    type="mini"
                    size={IconSize.SMALL}
                  />
                  <h1 className="file-preview__title">
                    {removeFileExtension(currentFile.title)}
                  </h1>
                </div>
              </div>
              <div className="file-preview__header__content__right">
                {customHeaderActions
                  ? customHeaderActions(headerActions)
                  : headerActions}
              </div>
            </div>
          </div>
          <div className="file-preview__content">
            <div className="file-preview__main">
              <EncryptedFileViewer
                file={currentFile}
                onDownload={handleDownload}
              />
              <div className="file-preview__previous-button">
                <Button
                  onClick={goPrevious}
                  disabled={!hasPrevious}
                  icon={<Icon name="arrow_back" />}
                  color="brand"
                  variant="tertiary"
                  size="small"
                />
              </div>
              <div className="file-preview__next-button">
                <Button
                  onClick={goNext}
                  disabled={!hasNext}
                  icon={<Icon name="arrow_forward" />}
                  color="brand"
                  variant="tertiary"
                  size="small"
                />
              </div>
            </div>
            <div
              className={clsx("file-preview-sidebar", isSidebarOpen && "open")}
            >
              {sidebarContent}
            </div>
          </div>
        </div>
      </div>
    </Modal>
  );
};
