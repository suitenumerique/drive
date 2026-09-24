import {
  getEffectiveMimetype,
  getMimeCategory,
  MimeCategory,
} from "@/features/explorer/utils/mimeTypes";
import { useDecryptedContent } from "@/features/items/hooks/useDecryptedContent";
import { Item } from "@/features/drivers/types";
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
import { Button, Loader } from "@gouvfr-lasuite/cunningham-react";
import { EncryptionState } from "@/features/encryption/EncryptionLayout";

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
      <EncryptionState
        illustration="document-encrypting"
        title={t(
          "explorer.encrypted.pending_self.title",
          "Enable encryption to open this file",
        )}
        description={t(
          "explorer.encrypted.pending_self.body",
          "This file is encrypted. Enable encryption from your profile menu, then a collaborator who already has access will accept you from the share dialog.",
        )}
      />
    );
  }

  const effectiveMimetype =
    getEffectiveMimetype(
      file as unknown as Parameters<typeof getEffectiveMimetype>[0],
    ) ?? file.mimetype;

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
    return <OOEditor item={itemLike as unknown as Item} />;
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
  const { openEncryptionOnboarding, error: vaultClientError } =
    useVaultClient();
  const category = getMimeCategory(effectiveMimetype);

  // Non-office files: decrypt and display with native viewers
  // Pass item-like object to the hook
  const item = {
    id: file.id,
    url: file.url,
    is_encrypted: true,
    mimetype: file.mimetype,
  };
  const { blobUrl, isDecrypting, error } = useDecryptedContent(
    item as unknown as Item,
  );

  // No SDK, no decryption: say so rather than "enable encryption".
  if (vaultClientError) {
    return (
      <EncryptionState
        title={t(
          "encryption.service_unavailable.title",
          "Encryption service unavailable",
        )}
        description={t(
          "encryption.service_unavailable.viewer_body",
          "This file is encrypted and the encryption service could not be loaded. Check your connection and try again.",
        )}
        actions={
          <Button
            size="small"
            variant="tertiary"
            onClick={() => window.location.reload()}
          >
            {t("encryption.service_unavailable.retry", "Retry")}
          </Button>
        }
      />
    );
  }

  if (isDecrypting) {
    return (
      <EncryptionState
        title={t("explorer.encrypted.decrypting", "Decrypting...")}
      >
        <Loader />
      </EncryptionState>
    );
  }

  if (error) {
    if (isWrongSecretKeyError(error)) {
      return (
        <KeyMismatchPanel
          shareTimeVersion={file.encryption_public_key_version_for_user}
        />
      );
    }
    if (isMissingKeysError(error)) {
      return <MissingEncryptionKeysPanel onSetUp={openEncryptionOnboarding} />;
    }
    return (
      <EncryptionState
        title={t("explorer.encrypted.error", "Failed to decrypt file")}
        description={error.message}
      />
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
