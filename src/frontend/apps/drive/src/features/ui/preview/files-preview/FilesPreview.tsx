import {
  getMimeCategory,
  MimeCategory,
  removeFileExtension,
} from "@/features/explorer/utils/mimeTypes";
import { Icon, IconType } from "@gouvfr-lasuite/ui-kit";
import { Button } from "@openfun/cunningham-react";
import React, { useEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";
import { ImageViewer } from "../image-viewer/ImageViewer";
import { VideoPlayer } from "../video-player/VideoPlayer";
import { AudioPlayer } from "../audio-player/AudioPlayer";
import { PreviewPdf } from "../pdf-preview/PreviewPdf";

import { NotSupportedPreview } from "../not-supported/NotSupportedPreview";
import { getIconByMimeType } from "@/features/explorer/components/icons/ItemIcon";
import { useTranslation } from "react-i18next";
import { downloadFile } from "@/features/items/utils";

export type FilePreviewType = {
  id: string;
  title: string;
  mimetype: string;
  url: string;
};

type FilePreviewData = FilePreviewType & {
  category: MimeCategory;
};

interface FilePreviewProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  files?: FilePreviewType[];
  initialIndexFile?: number;
  openedFileId?: string;
  headerRightContent?: React.ReactNode;
  sidebarContent?: React.ReactNode;
  onChangeFile?: (file?: FilePreviewType) => void;
}

export const FilePreview = ({
  isOpen,
  onClose,
  title = "File Preview",
  files = [],
  initialIndexFile = 0,
  openedFileId,
  sidebarContent,
  headerRightContent,
  onChangeFile,
}: FilePreviewProps) => {
  const { t } = useTranslation();
  const [currentIndex, setCurrentIndex] = useState(initialIndexFile);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  const data: FilePreviewData[] = useMemo(() => {
    return files?.map((file) => ({
      ...file,
      category: getMimeCategory(file.mimetype),
    }));
  }, [files]);

  const currentFile: FilePreviewData | null = data[currentIndex] || null;

  const handleDownload = async () => {
    downloadFile(currentFile.url, currentFile.title);
  };

  // Render the appropriate viewer based on file category
  const renderViewer = () => {
    if (!currentFile) {
      return <div>{t("file_preview.unsupported.title")}</div>;
    }

    switch (currentFile.category) {
      case MimeCategory.IMAGE:
        return (
          <ImageViewer
            src={currentFile.url}
            alt={currentFile.title}
            className="file-preview-viewer"
          />
        );
      case MimeCategory.VIDEO:
        return (
          <div className="video-preview-viewer-container">
            <div className="video-preview-viewer">
              <VideoPlayer
                src={currentFile.url}
                className="file-preview-viewer"
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
                src={currentFile.url}
                title={currentFile.title}
                className="file-preview-viewer"
              />
            </div>
          </div>
        );
      case MimeCategory.PDF:
        return <PreviewPdf src={currentFile.url} />;
      default:
        return <NotSupportedPreview file={currentFile} />;
    }
  };

  useEffect(() => {
    if (openedFileId) {
      const index = data.findIndex((file) => file.id === openedFileId);
      setCurrentIndex(index > -1 ? index : 0);
    }
  }, [openedFileId]);

  useEffect(() => {
    onChangeFile?.(currentFile);
  }, [currentFile]);

  if (!isOpen) {
    return null;
  }

  const previewContent = (
    <div className="file-preview-overlay">
      <div
        className={`file-preview-container ${
          isSidebarOpen ? "sidebar-open" : ""
        }`}
      >
        <div className="file-preview-header">
          <div className="file-preview-header__content">
            <div className="file-preview-header__content-left">
              <Button
                color="tertiary-text"
                size="small"
                onClick={onClose}
                icon={<Icon name="close" />}
              />

              <div className="file-preview-title">
                <img
                  src={getIconByMimeType(currentFile.mimetype, "mini").src}
                  alt=""
                  width={24}
                  className={`item-icon`}
                  draggable="false"
                />
                <h1 className="file-preview-title">
                  {removeFileExtension(currentFile?.title || title)}
                </h1>
              </div>
            </div>
            <div className="file-preview-header__content-center">
              <FilePreviewNav
                currentIndex={currentIndex}
                totalFiles={data.length}
                onPrevious={() => setCurrentIndex(currentIndex - 1)}
                onNext={() => setCurrentIndex(currentIndex + 1)}
              />
            </div>
            <div className="file-preview-header__content-right">
              {headerRightContent}
              <Button
                color="tertiary-text"
                onClick={handleDownload}
                icon={<Icon type={IconType.OUTLINED} name={"file_download"} />}
              />

              <Button
                color="tertiary-text"
                onClick={() => setIsSidebarOpen(!isSidebarOpen)}
                icon={<Icon name={"info_outline"} />}
              />
            </div>
          </div>
        </div>
        <div className="file-preview-content">
          <div className="file-preview-main">{renderViewer()}</div>

          <div
            className={`file-preview-sidebar ${isSidebarOpen ? "open" : ""}`}
          >
            {sidebarContent}
          </div>
        </div>
      </div>
    </div>
  );

  // Use Portal to render the preview outside the component hierarchy
  return <>{createPortal(previewContent, document.body)}</>;
};

interface FilePreviewNavProps {
  currentIndex: number;
  totalFiles: number;
  onPrevious: () => void;
  onNext: () => void;
}

export const FilePreviewNav: React.FC<FilePreviewNavProps> = ({
  currentIndex,
  totalFiles,
  onPrevious,
  onNext,
}) => {
  return (
    <div className="file-preview-nav">
      <Button
        color="tertiary-text"
        onClick={onPrevious}
        disabled={currentIndex === 0}
        icon={<Icon name="arrow_back" />}
      />
      <span className="file-preview-nav__count">
        {currentIndex + 1} / {totalFiles}
      </span>
      <Button
        color="tertiary-text"
        onClick={onNext}
        disabled={currentIndex === totalFiles - 1}
        icon={<Icon name="arrow_forward" />}
      />
    </div>
  );
};
