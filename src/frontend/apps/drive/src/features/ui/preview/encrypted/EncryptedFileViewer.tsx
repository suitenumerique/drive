import {
  Button,
  FilePreviewType,
  getMimeCategory,
  ImageViewer,
  Loader,
  MimeCategory,
  NotSupportedPreview,
  AudioPlayer,
  VideoPlayer,
  useCustomTranslations,
} from "@gouvfr-lasuite/ui-components";
import { getEffectiveMimetype } from "@/features/explorer/utils/mimeTypes";
import { useItem } from "@/features/explorer/hooks/useQueries";
import { useDecryptedContent } from "@/features/items/hooks/useDecryptedContent";
import { Item } from "@/features/drivers/types";
import { useTranslation } from "react-i18next";
import { OOEditor } from "@/features/encryption/oo-bridge/OOEditor";
import { MIME_TO_DOC_TYPE } from "@/features/encryption/oo-bridge/types";
import {
  DecryptionFailurePanel,
  decryptionFailureOf,
} from "@/features/encryption/DecryptionFailurePanel";
import {
  EnableEncryptionButton,
  EncryptionHomeButton,
  isMissingKeysError,
  MissingEncryptionKeysPanel,
} from "@/features/encryption/MissingEncryptionKeysModal";
import { useVaultClient } from "@/features/encryption/VaultClientProvider";
import { EncryptionState } from "@/features/encryption/EncryptionLayout";

/**
 * The design system's preview file, plus what the encrypted viewers read off
 * the item (`itemToPreviewFile` fills them in).
 */
export type EncryptedPreviewFile = FilePreviewType & {
  filename?: string;
  is_encrypted?: boolean;
  is_pending_encryption_for_user?: boolean;
  encryption_public_key_version_for_user?: number | null;
  abilities?: {
    partial_update?: boolean;
    update?: boolean;
    destroy?: boolean;
    encrypt?: boolean;
    remove_encryption?: boolean;
  };
};

interface EncryptedFileViewerProps {
  file: EncryptedPreviewFile;
  onDownload?: () => void;
}

// How often a pending member's viewer checks whether they got the key.
const PENDING_RECHECK_MS = 15_000;

/**
 * Viewer for encrypted files.
 *
 * Fetches the encrypted content from S3, decrypts it client-side via the
 * vault, and renders the appropriate viewer using a blob URL.
 * The decrypted content never leaves the browser: no plaintext on S3.
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

  // A pending member gets the key when someone who can manage members opens
  // the item elsewhere: look again now and then, and when the tab comes back,
  // so the file opens by itself once they have. The file handed in is a
  // snapshot (a list row), hence the item's own query.
  const { data: latest } = useItem(file.id, {
    enabled: !!file.is_pending_encryption_for_user,
    refetchInterval: (query) =>
      query.state.data?.is_pending_encryption_for_user === false
        ? false
        : PENDING_RECHECK_MS,
  });
  const isPending =
    !!file.is_pending_encryption_for_user &&
    (latest?.id !== file.id || latest.is_pending_encryption_for_user);

  // Pending member: no key was wrapped for this user yet (they had no
  // encryption when they were added). Render the explanation directly: don't
  // try to decrypt, don't call /key-chain/ (which would 403 and trigger the
  // global /403 redirect).
  if (isPending) {
    // Whether this device has keys decides the whole state (its title, its
    // action): until the vault answers, a loader rather than a guess.
    if (!vaultClientError && hasKeys === null) {
      return (
        <div className="drive__encryption-state">
          <Loader />
        </div>
      );
    }
    return (
      <EncryptionState
        illustration="document-encrypting"
        // Without keys the next step is the user's own, as for any encrypted
        // file on a device without keys: only once they enabled encryption
        // are they waiting for someone else.
        title={
          hasKeys
            ? t("explorer.encrypted.pending_self.title", "Waiting for access")
            : t("encryption.missing_keys.viewer_title", "Encrypted file")
        }
        description={
          hasKeys
            ? t(
                "explorer.encrypted.pending_self.body_with_keys",
                "This file was shared with you before you enabled encryption, so its key could not be given to you then. You will get access the next time the file owner opens it.",
              )
            : t(
                "explorer.encrypted.pending_self.body_without_keys",
                "This file is encrypted and you have not enabled encryption yet, so its key could not be given to you. Enable encryption: you will get access the next time the file owner opens it.",
              )
        }
        actions={
          <>
            <EncryptionHomeButton />
            {!hasKeys && (
              <EnableEncryptionButton
                size="small"
                onClick={openEncryptionOnboarding}
              />
            )}
          </>
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
  // Use the OO bridge's own MIME_TO_DOC_TYPE as the source of truth: it covers
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
    <DecryptedFileContent
      file={file}
      effectiveMimetype={effectiveMimetype}
      onDownload={onDownload}
    />
  );
};

interface DecryptedFileContentProps {
  file: EncryptedPreviewFile;
  effectiveMimetype: string;
  onDownload?: () => void;
}

const DecryptedFileContent = ({
  file,
  effectiveMimetype,
  onDownload,
}: DecryptedFileContentProps) => {
  const { t } = useTranslation();
  const { t: tPreview } = useCustomTranslations();
  const { openEncryptionOnboarding, error: vaultClientError } =
    useVaultClient();
  const category = getMimeCategory(effectiveMimetype);

  // Decrypt and display with native viewers
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
            title={tPreview("components.filePreview.unsupported.heicTitle")}
            file={file}
            onDownload={onDownload}
          />
        );
      }
      return (
        <ImageViewer
          src={blobUrl}
          alt={file.title}
          className="file-preview__viewer"
        />
      );
    case MimeCategory.VIDEO:
      return (
        <div
          className="video-preview-viewer-container"
          data-preview-backdrop="true"
        >
          <div className="video-preview-viewer">
            <VideoPlayer
              src={blobUrl}
              className="file-preview__viewer"
              controls={true}
            />
          </div>
        </div>
      );
    case MimeCategory.AUDIO:
      return (
        <div
          className="video-preview-viewer-container"
          data-preview-backdrop="true"
        >
          <div className="video-preview-viewer">
            <AudioPlayer
              src={blobUrl}
              title={file.title}
              className="file-preview__viewer"
            />
          </div>
        </div>
      );
    case MimeCategory.PDF:
      // The design system's PDF viewer is not exported: the browser's own
      // viewer reads the decrypted blob instead.
      return (
        <iframe
          src={blobUrl}
          title={file.title}
          width="100%"
          height="100%"
          className="drive__encrypted-pdf"
        />
      );
    default:
      return <NotSupportedPreview file={file} onDownload={onDownload} />;
  }
};
