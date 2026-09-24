import {
  Alert,
  Button,
  Modal,
  ModalSize,
  VariantType,
} from "@gouvfr-lasuite/cunningham-react";
import { useTranslation } from "react-i18next";
import { Item, ItemType } from "@/features/drivers/types";
import { useRecursiveEncryptionJob } from "./recursive/useRecursiveEncryptionJob";
import { JobFileRow } from "./recursive/JobFileRow";
import { JobSummary } from "./recursive/JobSummary";
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

  const title =
    item.type === ItemType.FOLDER
      ? t(
          "encryption.remove_modal.title_folder",
          'Remove encryption from folder "{{title}}"',
          { title: item.title },
        )
      : t(
          "encryption.remove_modal.title_file",
          'Remove encryption from file "{{title}}"',
          { title: item.title },
        );

  const busy =
    job.phase === "discovering" ||
    job.phase === "validating" ||
    job.phase === "staging" ||
    job.phase === "committing";

  const hasValidation = job.validationErrors.length > 0;

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      closeOnClickOutside={!busy}
      size={ModalSize.MEDIUM}
      aria-label={title}
    >
      <EncryptionModalContent
        illustration="document-shield-x"
        title={title}
        description={
          job.phase === "ready"
            ? t(
                "encryption.remove_modal.description",
                "The content will be decrypted and stored in plain text on the server.",
              )
            : undefined
        }
        actions={
          <>
            {job.phase === "ready" && (
              <Button onClick={() => job.confirm()} disabled={!job.canConfirm}>
                {t("encryption.remove_modal.confirm", "Remove encryption")}
              </Button>
            )}
            {job.phase === "failed" && (
              <Button onClick={() => job.retry()}>
                {t("common.retry", "Retry")}
              </Button>
            )}
            <Button
              variant="bordered"
              color="neutral"
              onClick={() => {
                if (busy) job.cancel();
                onClose();
              }}
            >
              {busy ? t("common.cancel", "Cancel") : t("common.close", "Close")}
            </Button>
          </>
        }
      >
        {hasValidation && (
          <Alert type={VariantType.ERROR}>
            <ul style={{ margin: 0, paddingLeft: "1.25rem" }}>
              {job.validationErrors.map((e, i) => (
                <li key={i}>{e}</li>
              ))}
            </ul>
          </Alert>
        )}

        {job.topError && <Alert type={VariantType.ERROR}>{job.topError}</Alert>}

        <JobSummary
          phase={job.phase}
          total={job.totalProcessable}
          done={job.doneCount}
          skipped={job.skippedCount}
          failed={job.failedCount}
          mode="decrypt"
        />

        {job.rows.length > 0 && job.rows.length <= 50 && (
          <div className="drive__encryption-modal__rows">
            {job.rows.map((r) => (
              <JobFileRow row={r} key={r.id} />
            ))}
          </div>
        )}
        {job.rows.length > 50 && (
          <p className="drive__encryption-modal__hint">
            {t(
              "encryption.remove_modal.large_set",
              "{{count}} items in this folder. Per-item progress is hidden for large jobs — see the summary above.",
              { count: job.rows.length },
            )}
          </p>
        )}
      </EncryptionModalContent>
    </Modal>
  );
};
