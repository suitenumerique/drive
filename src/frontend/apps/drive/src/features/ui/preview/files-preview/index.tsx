import {
  getMimeCategory,
  MimeCategory,
} from "@/features/explorer/utils/mimeTypes";
import { Icon } from "@gouvfr-lasuite/ui-kit";
import { Button } from "@openfun/cunningham-react";
import React, { useMemo, useState } from "react";
import { ImageViewer } from "../image-viewer/ImageViewer";
import { VideoPlayer } from "../video-player/VideoPlayer";
import { AudioPlayer } from "../audio-player";
import { PreviewPdf } from "../pdf-preview/PreviewPdf";
import { getIconByMimeType } from "@/features/explorer/components/ItemIcon";

type FilePreviewType = {
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
  headerRightContent?: React.ReactNode;
}

export const FilePreview: React.FC<FilePreviewProps> = ({
  isOpen,
  onClose,
  title = "File Preview",
  files = [],
  initialIndexFile = 0,
}) => {
  const [currentIndex, setCurrentIndex] = useState(initialIndexFile);

  const data: FilePreviewData[] = useMemo(() => {
    return files?.map((file) => ({
      ...file,
      category: getMimeCategory(file.mimetype),
    }));
  }, [files]);

  const currentFile: FilePreviewData | null = data[currentIndex] || null;

  // Render the appropriate viewer based on file category
  const renderViewer = () => {
    if (!currentFile) {
      return <div>No file to preview</div>;
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
        return (
          <div className="file-preview-unsupported">
            <p>Type de fichier non supporté pour la prévisualisation</p>
            <p>Type: {currentFile.mimetype}</p>
            <a href={currentFile.url} target="_blank" rel="noopener noreferrer">
              Télécharger le fichier
            </a>
          </div>
        );
    }
  };

  if (!isOpen) {
    return null;
  }

  return (
    <div className="file-preview-overlay">
      <div className="file-preview-container">
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
                  {currentFile?.title || title}
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
              <button
                className="file-preview-close-button"
                onClick={onClose}
                aria-label="Close preview"
              >
                <svg
                  width="24"
                  height="24"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <line x1="18" y1="6" x2="6" y2="18"></line>
                  <line x1="6" y1="6" x2="18" y2="18"></line>
                </svg>
              </button>
            </div>
          </div>
        </div>
        <div className="file-preview-content">{renderViewer()}</div>
      </div>
    </div>
  );
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
