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

interface Props {
  isOpen: boolean;
  onClose: () => void;
  item: Item;
  /**
   * Optional — fires when the recursive-decryption job completes
   * successfully, BEFORE the auto-close timeout. Lets callers
   * distinguish "decryption succeeded" from "user closed without
   * completing" (the `onClose` path covers both).
   */
  onSuccess?: () => void;
}

export const ModalRecursiveRemoveEncryption = ({
  isOpen,
  onClose,
  item,
  onSuccess,
}: Props) => {
  const { t } = useTranslation();
  const job = useRecursiveEncryptionJob({
    mode: "decrypt",
    item,
    isOpen,
    onSuccess: () => {
      onSuccess?.();
      setTimeout(onClose, 1200);
    },
  });

  // The item itself is the list's first row: no need to repeat its name.
  const title =
    item.type === ItemType.FOLDER
      ? t(
          "encryption.remove_modal.title_folder",
          "Remove encryption from this folder",
        )
      : t(
          "encryption.remove_modal.title_file",
          "Remove encryption from this file",
        );

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

  return (
    <Modal
      isOpen={isOpen}
      onClose={close}
      closeOnClickOutside={!busy}
      size={ModalSize.MEDIUM}
      aria-label={`${title}: ${item.title}`}
    >
      <EncryptionModalContent
        illustration="document-shield-x"
        className={
          committing ? "drive__encryption-modal--committing" : undefined
        }
        title={title}
        description={t(
          "encryption.remove_modal.description",
          "The content will be decrypted and stored in plain text on the server.",
        )}
        actions={
          <>
            {/* One button for the whole job, so the modal keeps its height
                from opening to closing: only its label and state change. */}
            {job.phase === "failed" ? (
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
                {t("encryption.remove_modal.removing", "Removing encryption…")}
              </Button>
            ) : job.phase === "success" ? (
              <Button disabled>
                {t("encryption.remove_modal.done", "Encryption removed")}
              </Button>
            ) : (
              <Button onClick={() => job.confirm()} disabled={!job.canConfirm}>
                {t("encryption.remove_modal.confirm", "Remove encryption")}
              </Button>
            )}
          </>
        }
      >
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
              mode="decrypt"
            />
            <JobFileList rows={job.rows} mode="decrypt" />
          </>
        )}
      </EncryptionModalContent>
    </Modal>
  );
};
