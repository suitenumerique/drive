import {
  getMimeCategory,
  MimeCategory,
  removeFileExtension,
} from "@/features/explorer/utils/mimeTypes";
import { DropdownMenu, Icon, IconType } from "@gouvfr-lasuite/ui-kit";
import {
  Button,
  ButtonProps,
  Modal,
  ModalSize,
} from "@gouvfr-lasuite/cunningham-react";
import React, { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import posthog from "posthog-js";
import dynamic from "next/dynamic";
import clsx from "clsx";
import { VideoPlayer } from "./viewers/video-player/VideoPlayer";
import { AudioPlayer } from "./viewers/audio-player/AudioPlayer";
import { ImageViewer } from "./viewers/image-viewer/ImageViewer";
import { SuspiciousPreview } from "./viewers/suspicious/SuspiciousPreview";
import { NotSupportedPreview } from "./viewers/not-supported/NotSupportedPreview";
import { WopiOpenInEditor } from "./viewers/wopi/WopiOpenInEditor";
import { OPEN_DELAY } from "./viewers/pdf-preview/pdfConsts";
import { FileIcon } from "@/features/explorer/components/icons/ItemIcon";

const PreviewPdf = dynamic<{
  src: string;
  onThumbailSidebarOpen?: (isOpen: boolean) => void;
}>(
  () =>
    import("./viewers/pdf-preview/PdfPreview")
      .then((mod) => mod.PdfPreview)
      .catch(() => {
        const {
          OutdatedBrowserPreview,
          // eslint-disable-next-line @typescript-eslint/no-require-imports
        } = require("./viewers/pdf-preview/OutdatedBrowserPreview");
        return OutdatedBrowserPreview;
      }),
  {
    ssr: false,
  },
);
export type FilePreviewType = {
  id: string;
  size: number;
  title: string;
  mimetype: string;
  is_wopi_supported?: boolean;
  url_preview: string;
  url: string;
};

type FilePreviewData = FilePreviewType & {
  category: MimeCategory;
  isSuspicious?: boolean;
};

interface FilePreviewProps {
  isOpen: boolean;
  onClose?: () => void;
  title?: string;
  files?: FilePreviewType[];
  initialIndexFile?: number;
  openedFileId?: string;
  headerRightContent?: React.ReactNode;
  sidebarContent?: React.ReactNode;
  onChangeFile?: (file?: FilePreviewType) => void;
  handleDownloadFile?: (file?: FilePreviewType) => void;
  hideCloseButton?: boolean;
}

export const FilePreview = ({
  isOpen,
  onClose,
  title = "File Preview",
  files = [],
  initialIndexFile = -1,
  openedFileId,
  sidebarContent,
  headerRightContent,
  onChangeFile,
  handleDownloadFile,
  hideCloseButton,
}: FilePreviewProps) => {
  const { t } = useTranslation();
  const [currentIndex, setCurrentIndex] = useState(initialIndexFile);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [classNames, setClassNames] = useState<string[]>([]);
  const [pdfThumbnailSidebarOpen, setPdfThumbnailSidebarOpen] = useState(false);
  const [isActionsMenuOpen, setIsActionsMenuOpen] = useState(false);

  const data: FilePreviewData[] = useMemo(() => {
    return files?.map((file) => ({
      ...file,
      is_wopi_supported: file.is_wopi_supported ?? false,
      category: getMimeCategory(file.mimetype),
    }));
  }, [files]);

  const currentFile: FilePreviewData | undefined =
    currentIndex > -1 ? data[currentIndex] : undefined;

  const canGoNext = currentIndex < data.length - 1;
  const canGoPrevious = currentIndex > 0;

  const goToNext = () => {
    if (canGoNext) setCurrentIndex(currentIndex + 1);
  };

  const goToPrevious = () => {
    if (canGoPrevious) setCurrentIndex(currentIndex - 1);
  };

  const handleDownload = async () => {
    handleDownloadFile?.(currentFile);
  };

  const handlePrint = () => {
    if (!currentFile) return;
    window.open(currentFile.url_preview, "_blank");
  };

  // Render the appropriate viewer based on file category
  const renderViewer = () => {
    if (!currentFile) {
      return <div>{t("file_preview.unsupported.title")}</div>;
    }

    if (currentFile.isSuspicious) {
      return <SuspiciousPreview handleDownload={handleDownload} />;
    }
    if (currentFile.is_wopi_supported) {
      return <WopiOpenInEditor file={currentFile} />;
    }

    switch (currentFile.category) {
      case MimeCategory.IMAGE:
        if (currentFile.mimetype.includes("heic")) {
          return (
            <NotSupportedPreview
              title={t("file_preview.unsupported.heic_title")}
              file={currentFile}
              onDownload={handleDownload}
            />
          );
        }

        return (
          <ImageViewer
            src={currentFile.url_preview}
            alt={currentFile.title}
            className="file-preview__viewer"
          />
        );
      case MimeCategory.VIDEO:
        return (
          <div className="video-preview-viewer-container">
            <div className="video-preview-viewer">
              <VideoPlayer
                src={currentFile.url_preview}
                className="file-preview__viewer"
                controls={true}
              />
            </div>
          </div>
        );
      case MimeCategory.AUDIO:
        return (
          <div className="video-preview-viewer-container">
            <div className="video-preview-viewer">
              <AudioPlayer
                src={currentFile.url_preview}
                title={currentFile.title}
                className="file-preview__viewer"
              />
            </div>
          </div>
        );
      case MimeCategory.PDF:
        return (
          <PreviewPdf
            src={currentFile.url_preview}
            onThumbailSidebarOpen={(isOpen) => {
              setPdfThumbnailSidebarOpen(isOpen);
            }}
          />
        );

      default:
        return (
          <NotSupportedPreview file={currentFile} onDownload={handleDownload} />
        );
    }
  };

  // Add a specific class name to the container when the PDF thumbnail sidebar is open.
  // So the navigation buttons can move in sync.
  useEffect(() => {
    const className = "file-preview__container--pdf-sidebar-open";
    const isPdf = currentFile?.category === MimeCategory.PDF;
    let timeoutId: ReturnType<typeof setTimeout> | undefined;
    if (pdfThumbnailSidebarOpen && isPdf) {
      // The timeout is set so that the thumbnail sidebar and the button move in sync.
      timeoutId = setTimeout(() => {
        setClassNames((prev) => {
          if (prev.includes(className)) {
            return prev;
          }
          return [...prev, className];
        });
      }, OPEN_DELAY);
    } else {
      setClassNames((prev) => {
        return prev.filter((className_) => className_ !== className);
      });
    }

    // When switching from a PDF to a non-PDF file, we mark the thumbnail sidebar as closed.
    if (pdfThumbnailSidebarOpen && !isPdf) {
      setPdfThumbnailSidebarOpen(false);
    }

    return () => {
      if (timeoutId) {
        clearTimeout(timeoutId);
      }
    };
  }, [pdfThumbnailSidebarOpen, currentFile]);

  useEffect(() => {
    if (openedFileId) {
      const index = data.findIndex((file) => file.id === openedFileId);
      const newIndex = index > -1 ? index : -1;
      setCurrentIndex(newIndex);
    } else {
      setCurrentIndex(-1);
    }
  }, [openedFileId]);

  useEffect(() => {
    onChangeFile?.(currentFile);
    if (currentFile) {
      posthog.capture("file_preview_opened", {
        id: currentFile.id,
        size: currentFile.size,
        mimetype: currentFile.mimetype,
      });
    }
  }, [currentFile]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Prevent navigation if the target is a player timeline.
      const tag = (e.target as HTMLElement)?.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") {
        return;
      }

      if (e.key === "ArrowLeft") {
        e.preventDefault();
        goToPrevious();
      } else if (e.key === "ArrowRight") {
        e.preventDefault();
        goToNext();
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [currentIndex, data.length, currentFile?.category]);

  useEffect(() => {
    if (!isOpen || !currentFile) return;
    const previousTitle = document.title;
    document.title = `${currentFile.title} - ${t("app_title")}`;
    return () => {
      document.title = previousTitle;
    };
  }, [isOpen, currentFile, t]);

  if (!isOpen || !currentFile) {
    return null;
  }

  return (
    <Modal
      isOpen={isOpen}
      onClose={() => onClose?.()}
      size={ModalSize.FULL}
      hideCloseButton={true}
    >
      <div data-testid="file-preview">
        <div
          className={clsx(
            "file-preview__container",
            isSidebarOpen && "file-preview__container--sidebar-open",
            classNames,
          )}
        >
          <div className="file-preview__header">
            <div className="file-preview__header__content">
              <div className="file-preview__header__content__left">
                {!hideCloseButton && (
                  <Button
                    variant="tertiary"
                    size="small"
                    onClick={onClose}
                    icon={<Icon name="close" />}
                  />
                )}

                <div className="file-preview__title-wrapper">
                  <FileIcon file={currentFile} type="mini" size="small" />
                  <h1 className="file-preview__title">
                    {removeFileExtension(currentFile?.title || title)}
                  </h1>
                </div>
              </div>
              <div className="file-preview__header__content__right">
                {headerRightContent}
                {handleDownloadFile && (
                  <Button
                    variant="tertiary"
                    onClick={handleDownload}
                    icon={
                      <Icon type={IconType.OUTLINED} name={"file_download"} />
                    }
                  />
                )}
                <Button
                  variant="tertiary"
                  onClick={() => setIsSidebarOpen(!isSidebarOpen)}
                  icon={<Icon name={"info_outline"} />}
                />
                {(currentFile?.category === MimeCategory.PDF ||
                  currentFile?.category === MimeCategory.IMAGE) && (
                  <DropdownMenu
                    options={[
                      ...(handleDownloadFile
                        ? [
                            {
                              icon: (
                                <Icon
                                  type={IconType.OUTLINED}
                                  name="file_download"
                                />
                              ),
                              label: t("file_preview.actions.download"),
                              value: "download",
                              callback: handleDownload,
                            },
                          ]
                        : []),
                      {
                        icon: <Icon name="print" />,
                        label: t("file_preview.actions.print"),
                        value: "print",
                        callback: handlePrint,
                      },
                    ]}
                    isOpen={isActionsMenuOpen}
                    onOpenChange={setIsActionsMenuOpen}
                  >
                    <Button
                      variant="tertiary"
                      onClick={() => setIsActionsMenuOpen(!isActionsMenuOpen)}
                      icon={<Icon name="more_vert" />}
                    />
                  </DropdownMenu>
                )}
              </div>
            </div>
          </div>
          <div className="file-preview__content">
            <div className="file-preview__main">
              {renderViewer()}
              <FilePreviewPreviousButton
                onClick={goToPrevious}
                disabled={!canGoPrevious}
              />
              <FilePreviewNextButton onClick={goToNext} disabled={!canGoNext} />
            </div>

            <div
              className={`file-preview-sidebar ${isSidebarOpen ? "open" : ""}`}
            >
              {sidebarContent}
            </div>
          </div>
        </div>
      </div>
    </Modal>
  );
};

const FilePreviewNextButton = (props: Partial<ButtonProps>) => {
  return (
    <div className="file-preview__next-button">
      <Button
        {...props}
        icon={<Icon name="arrow_forward" />}
        color="brand"
        variant="tertiary"
        size="small"
      />
    </div>
  );
};

const FilePreviewPreviousButton = (props: Partial<ButtonProps>) => {
  return (
    <div className="file-preview__previous-button">
      <Button
        {...props}
        icon={<Icon name="arrow_back" />}
        color="brand"
        variant="tertiary"
        size="small"
      />
    </div>
  );
};
