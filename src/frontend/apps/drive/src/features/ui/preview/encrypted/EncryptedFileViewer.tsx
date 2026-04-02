import {
  getMimeCategory,
  MimeCategory,
} from "@/features/explorer/utils/mimeTypes";
import { useDecryptedContent } from "@/features/items/hooks/useDecryptedContent";
import { useTranslation } from "react-i18next";
import { ImageViewer } from "../image-viewer/ImageViewer";
import { VideoPlayer } from "../video-player/VideoPlayer";
import { AudioPlayer } from "../audio-player/AudioPlayer";
import { PreviewPdf } from "../pdf-preview/PreviewPdf";
import { NotSupportedPreview } from "../not-supported/NotSupportedPreview";
import { type FilePreviewType } from "../files-preview/FilesPreview";
import { Loader } from "@gouvfr-lasuite/cunningham-react";

interface EncryptedFileViewerProps {
  file: FilePreviewType;
  onDownload?: () => void;
}

/**
 * Viewer for encrypted files.
 *
 * Fetches the encrypted content from S3, decrypts it client-side via the
 * vault, and renders the appropriate viewer using a blob URL.
 * The decrypted content never leaves the browser — no plaintext on S3.
 */
export const EncryptedFileViewer = ({
  file,
  onDownload,
}: EncryptedFileViewerProps) => {
  const { t } = useTranslation();

  // Pass item-like object to the hook
  const item = {
    id: file.id,
    url: file.url,
    is_encrypted: true,
    mimetype: file.mimetype,
  };
  const { blobUrl, isDecrypting, error } = useDecryptedContent(item as any);

  if (isDecrypting) {
    return (
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          height: "100%",
          gap: "16px",
        }}
      >
        <Loader />
        <span
          style={{
            display: "flex",
            alignItems: "center",
            gap: "8px",
            color: "var(--c--theme--colors--success-600, #18753c)",
          }}
        >
          <span className="material-icons" style={{ fontSize: "20px" }}>
            lock
          </span>
          {t("explorer.encrypted.decrypting", "Decrypting...")}
        </span>
      </div>
    );
  }

  if (error) {
    return (
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          height: "100%",
          gap: "16px",
        }}
      >
        <span className="material-icons" style={{ fontSize: "48px", color: "var(--c--theme--colors--danger-600)" }}>
          error
        </span>
        <span>{t("explorer.encrypted.error", "Failed to decrypt file")}</span>
        <span style={{ fontSize: "12px", color: "var(--c--theme--colors--greyscale-600)" }}>
          {error.message}
        </span>
      </div>
    );
  }

  if (!blobUrl) {
    return null;
  }

  const category = getMimeCategory(file.mimetype);

  switch (category) {
    case MimeCategory.IMAGE:
      if (file.mimetype.includes("heic")) {
        return (
          <NotSupportedPreview
            title={t("file_preview.unsupported.heic_title")}
            file={file}
            onDownload={onDownload}
          />
        );
      }
      return (
        <ImageViewer
          src={blobUrl}
          alt={file.title}
          className="file-preview-viewer"
        />
      );
    case MimeCategory.VIDEO:
      return (
        <div className="video-preview-viewer-container">
          <div className="video-preview-viewer">
            <VideoPlayer
              src={blobUrl}
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
              src={blobUrl}
              title={file.title}
              className="file-preview-viewer"
            />
          </div>
        </div>
      );
    case MimeCategory.PDF:
      return <PreviewPdf src={blobUrl} />;
    default:
      return <NotSupportedPreview file={file} onDownload={onDownload} />;
  }
};
