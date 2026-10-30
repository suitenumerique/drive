import {
  Alert,
  Button,
  Modal,
  ModalSize,
  VariantType,
} from "@gouvfr-lasuite/ui-components";
import { useTranslation } from "react-i18next";
import { Item, ItemType } from "@/features/drivers/types";
import { useRecursiveEncryptionJob } from "./recursive/useRecursiveEncryptionJob";
import { JobFileList } from "./recursive/JobFileList";
import { JobProgressBar } from "./recursive/JobProgressBar";
import { EncryptionModalContent } from "./EncryptionLayout";
import { EnableEncryptionButton } from "./MissingEncryptionKeysModal";
import { useVaultClient } from "./VaultClientProvider";

interface Props {
  isOpen: boolean;
  onClose: () => void;
  item: Item;
  /**
   * Optional — fires when the recursive-encryption job completes
   * successfully, BEFORE the auto-close timeout fires. Lets callers
   * distinguish "encryption succeeded" from "user closed without
   * completing" (the `onClose` path covers both).
   */
  onSuccess?: () => void;
  /**
   * When set, the modal switches to encrypt-on-move mode: the item is
   * encrypted AND moved into the destination parent in one atomic
   * commit. Skips per-user wrap materialisation (no inherited
   * collaborator gets a wrap they didn't already have).
   */
  intoChainParentId?: string;
}

export const ModalRecursiveEncrypt = ({
  isOpen,
  onClose,
  item,
  onSuccess,
  intoChainParentId,
}: Props) => {
  const { t } = useTranslation();
  const { hasKeys, openEncryptionOnboarding } = useVaultClient();
  // Without keys on this device nothing can be encrypted: the action becomes
  // enabling encryption, and the user encrypts again once it is done.
  const needsKeys = hasKeys === false;
  const mode = intoChainParentId ? "encrypt-into-chain" : "encrypt";
  const job = useRecursiveEncryptionJob({
    mode,
    item,
    isOpen,
    intoChainParentId,
    onSuccess: () => {
      onSuccess?.();
      setTimeout(onClose, 1200);
    },
  });

  // The item itself is the list's first row: the title says what happens to
  // it, the destination intent included, without repeating its name.
  const title = intoChainParentId
    ? item.type === ItemType.FOLDER
      ? t(
          "encryption.encrypt_modal.title_folder_into_chain",
          "Encrypt and move this folder",
        )
      : t(
          "encryption.encrypt_modal.title_file_into_chain",
          "Encrypt and move this file",
        )
    : item.type === ItemType.FOLDER
      ? t("encryption.encrypt_modal.title_folder", "Encrypt this folder")
      : t("encryption.encrypt_modal.title_file", "Encrypt this file");

  const busy =
    job.phase === "discovering" ||
    job.phase === "validating" ||
    job.phase === "staging" ||
    job.phase === "committing";

  // The commit is one request the server completes in a transaction whether
  // or not the modal is still open: stay until it answers, so the user learns
  // the outcome. The close control stays in place, inactive (`preventClose`
  // would remove it for that moment). Closing before, while files are being
  // processed, cancels them and changes nothing on the item.
  const committing = job.phase === "committing";
  const close = () => {
    if (!committing) onClose();
  };

  const hasValidation = job.validationErrors.length > 0;

  const description =
    item.type === ItemType.FOLDER
      ? t(
          "encryption.encrypt_modal.description_folder",
          "The folder and everything inside will be encrypted end-to-end. Only people you share it with will be able to access its contents.",
        )
      : t(
          "encryption.encrypt_modal.description_file",
          "The file will be encrypted end-to-end. Only people you share it with will be able to access its contents.",
        );

  return (
    <Modal
      isOpen={isOpen}
      onClose={close}
      closeOnClickOutside={!busy}
      size={ModalSize.MEDIUM}
      aria-label={`${title}: ${item.title}`}
    >
      <EncryptionModalContent
        illustration={
          item.type === ItemType.FOLDER
            ? "folder-shield"
            : "document-shield-check"
        }
        className={
          committing ? "drive__encryption-modal--committing" : undefined
        }
        title={title}
        description={description}
        actions={
          <>
            {needsKeys && (
              <EnableEncryptionButton
                onClick={() => {
                  onClose();
                  openEncryptionOnboarding();
                }}
              />
            )}
            {/* One button for the whole job, so the modal keeps its height
                from opening to closing: only its label and state change. */}
            {!needsKeys &&
              (job.phase === "failed" ? (
                <Button onClick={() => job.retry()}>
                  {t("common.retry", "Retry")}
                </Button>
              ) : job.phase === "staging" ? (
                <Button
                  variant="bordered"
                  color="neutral"
                  onClick={() => {
                    job.cancel();
                    onClose();
                  }}
                >
                  {t("common.cancel", "Cancel")}
                </Button>
              ) : committing ? (
                <Button disabled>
                  {t("encryption.encrypt_modal.encrypting", "Encrypting…")}
                </Button>
              ) : job.phase === "success" ? (
                <Button disabled>
                  {t("encryption.encrypt_modal.done", "Encrypted")}
                </Button>
              ) : (
                <Button
                  onClick={() => job.confirm()}
                  disabled={!job.canConfirm}
                >
                  {intoChainParentId
                    ? t(
                        "encryption.encrypt_modal.confirm_into_chain",
                        "Encrypt & move",
                      )
                    : t("encryption.encrypt_modal.confirm", "Encrypt")}
                </Button>
              ))}
          </>
        }
      >
        {job.pendingUserCount > 0 &&
          (job.phase === "ready" || job.phase === "validating") && (
            <Alert type={VariantType.WARNING}>
              {t("encryption.encrypt_modal.pending_users", {
                count: job.pendingUserCount,
                defaultValue_one:
                  "{{count}} collaborator has not enabled encryption yet. They will be added as pending and get access once they enable it.",
                defaultValue_other:
                  "{{count}} collaborators have not enabled encryption yet. They will be added as pending and get access once they enable it.",
              })}
            </Alert>
          )}

        {hasValidation && (
          <Alert type={VariantType.ERROR}>
            {job.validationErrors.length === 1 ? (
              job.validationErrors[0]
            ) : (
              <ul
                style={{
                  margin: 0,
                  paddingLeft: "var(--c--globals--spacings--base)",
                }}
              >
                {job.validationErrors.map((e, i) => (
                  <li key={i}>{e}</li>
                ))}
              </ul>
            )}
          </Alert>
        )}

        {job.topError && <Alert type={VariantType.ERROR}>{job.topError}</Alert>}

        {job.retryNotice && (
          <Alert type={VariantType.INFO}>{job.retryNotice}</Alert>
        )}

        {job.phase !== "blocked" && job.rows.length > 0 && (
          <>
            <JobProgressBar
              phase={job.phase}
              total={job.totalProcessable}
              done={job.doneCount}
              mode="encrypt"
            />
            <JobFileList rows={job.rows} mode="encrypt" />
          </>
        )}
      </EncryptionModalContent>
    </Modal>
  );
};
