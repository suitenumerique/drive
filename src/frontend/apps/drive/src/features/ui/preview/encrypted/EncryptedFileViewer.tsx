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
  DecryptionFailurePanel,
  decryptionFailureOf,
} from "@/features/encryption/DecryptionFailurePanel";
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
  const {
    hasKeys,
    openEncryptionOnboarding,
    error: vaultClientError,
  } = useVaultClient();

  // Pending member: no key was wrapped for this user yet (the file was
  // encrypted before they enabled encryption). Render the explanation
  // directly: don't try to decrypt, don't call /key-chain/ (which would 403
  // and trigger the global /403 redirect).
  if (file.is_pending_encryption_for_user) {
    return (
      <EncryptionState
        illustration="document-encrypting"
        title={t("explorer.encrypted.pending_self.title", "Waiting for access")}
        description={
          hasKeys
            ? t(
                "explorer.encrypted.pending_self.body_with_keys",
                "This file was encrypted before you enabled encryption, so its key could not be shared with you then. You will get access the next time the file owner opens it.",
              )
            : t(
                "explorer.encrypted.pending_self.body_without_keys",
                "This file was encrypted before you enabled encryption, so its key could not be shared with you. Enable encryption on your account: you will get access the next time the file owner opens it.",
              )
        }
        actions={
          hasKeys ? undefined : (
            <Button
              size="small"
              variant="tertiary"
              onClick={openEncryptionOnboarding}
            >
              {t("encryption.missing_keys.set_up", "Enable encryption")}
            </Button>
          )
        }
      />
    );
  }

  // No keys on this device (or not known yet): nothing can be decrypted, so say
  // so up front instead of failing a decryption. Once onboarding completes,
  // `hasKeys` flips and the file below mounts, which starts its decryption.
  if (!vaultClientError && hasKeys === null) {
    return (
      <EncryptionState
        title={t("explorer.encrypted.decrypting", "Decrypting...")}
      >
        <Loader />
      </EncryptionState>
    );
  }
  if (!vaultClientError && !hasKeys) {
    return <MissingEncryptionKeysPanel onSetUp={openEncryptionOnboarding} />;
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
    encryption_public_key_version_for_user:
      file.encryption_public_key_version_for_user,
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
    if (
      isMissingKeysError(error) ||
      (error as VaultError).code === "UNRESOLVED_USER"
    ) {
      return <MissingEncryptionKeysPanel onSetUp={openEncryptionOnboarding} />;
    }
    return (
      <DecryptionFailurePanel
        failure={decryptionFailureOf((error as VaultError).code)}
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
