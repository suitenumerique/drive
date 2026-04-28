import {
  getEffectiveMimetype,
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
import { OOEditor } from "@/features/encryption/oo-bridge/OOEditor";
import { MIME_TO_DOC_TYPE } from "@/features/encryption/oo-bridge/types";
import {
  KeyMismatchPanel,
  isWrongSecretKeyError,
} from "@/features/encryption/KeyMismatchPanel";
import {
  isMissingKeysError,
  MissingEncryptionKeysPanel,
} from "@/features/encryption/MissingEncryptionKeysModal";
import { useVaultClient } from "@/features/encryption/VaultClientProvider";
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

  // Pending-onboarding short-circuit: the user has access to this
  // encrypted item but hasn't completed their vault setup yet. Render a
  // dedicated panel directly — don't try to decrypt, don't call
  // /key-chain/ (which would 403 and trigger the global /403 redirect).
  if (file.is_pending_encryption_for_user) {
    return (
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          height: "100%",
          gap: "16px",
          textAlign: "center",
          maxWidth: "420px",
          margin: "0 auto",
        }}
      >
        <span
          className="material-icons"
          style={{
            fontSize: "48px",
            color: "var(--c--theme--colors--warning-600, #b15600)",
          }}
        >
          hourglass_empty
        </span>
        <span style={{ fontWeight: 600 }}>
          {t(
            "explorer.encrypted.pending_self.title",
            "Complete your encryption onboarding to open this file",
          )}
        </span>
        <span
          style={{
            fontSize: "14px",
            color:
              "var(--c--contextuals--content--semantic--neutral--tertiary)",
          }}
        >
          {t(
            "explorer.encrypted.pending_self.body",
            "This file is encrypted and you haven't set up your encryption keys yet. First, complete your encryption onboarding from your profile menu — then a collaborator who already holds the decryption key will need to accept you from the share dialog before you can open this file.",
          )}
        </span>
      </div>
    );
  }

  // The server stores application/octet-stream for encrypted files (it
  // can't inspect ciphertext). Fall back to the extension-derived
  // mimetype so the right viewer / OO docType is picked.
  const effectiveMimetype =
    getEffectiveMimetype(file as unknown as Parameters<typeof getEffectiveMimetype>[0]) ??
    file.mimetype;

  // Office files: use OnlyOffice client-side editor (handles its own decryption).
  // Use the OO bridge's own MIME_TO_DOC_TYPE as the source of truth — it covers
  // formats like text/plain and text/csv that getMimeCategory classifies as OTHER.
  // Dispatched to a child component so the office and non-office paths
  // each have a stable hook order. Calling the OO branch as an early
  // `return` here while the non-office branch calls
  // `useDecryptedContent` would break the rules of hooks the moment a
  // user navigates from an office file to an image (or vice versa).
  const isOfficeFormat = effectiveMimetype in MIME_TO_DOC_TYPE;

  if (isOfficeFormat) {
    const itemLike = {
      ...file,
      id: file.id,
      title: file.title,
      is_encrypted: true,
    };
    return <OOEditor item={itemLike as any} />;
  }

  return (
    <NonOfficeEncryptedViewer
      file={file}
      effectiveMimetype={effectiveMimetype}
      onDownload={onDownload}
    />
  );
};

interface NonOfficeEncryptedViewerProps {
  file: FilePreviewType;
  effectiveMimetype: string;
  onDownload?: () => void;
}

const NonOfficeEncryptedViewer = ({
  file,
  effectiveMimetype,
  onDownload,
}: NonOfficeEncryptedViewerProps) => {
  const { t } = useTranslation();
  const { openEncryptionOnboarding } = useVaultClient();
  const category = getMimeCategory(effectiveMimetype);

  // Non-office files: decrypt and display with native viewers
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
    if (isWrongSecretKeyError(error)) {
      return (
        <KeyMismatchPanel
          shareTimeFingerprint={file.encryption_public_key_fingerprint_for_user}
        />
      );
    }
    if (isMissingKeysError(error)) {
      return (
        <MissingEncryptionKeysPanel onSetUp={openEncryptionOnboarding} />
      );
    }
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
