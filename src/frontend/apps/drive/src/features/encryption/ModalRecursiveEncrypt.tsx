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

  // Title surfaces the destination intent in the encrypt-on-move case
  // so the user knows the click will both encrypt and move.
  const title = intoChainParentId
    ? item.type === ItemType.FOLDER
      ? t(
          "encryption.encrypt_modal.title_folder_into_chain",
          'Encrypt and move folder "{{title}}"',
          { title: item.title },
        )
      : t(
          "encryption.encrypt_modal.title_file_into_chain",
          'Encrypt and move file "{{title}}"',
          { title: item.title },
        )
    : item.type === ItemType.FOLDER
      ? t(
          "encryption.encrypt_modal.title_folder",
          'Encrypt folder "{{title}}"',
          {
            title: item.title,
          },
        )
      : t("encryption.encrypt_modal.title_file", 'Encrypt file "{{title}}"', {
          title: item.title,
        });

  const busy =
    job.phase === "discovering" ||
    job.phase === "validating" ||
    job.phase === "staging" ||
    job.phase === "committing";

  const hasValidation = job.validationErrors.length > 0;

  const description =
    job.phase === "ready"
      ? item.type === ItemType.FOLDER
        ? t(
            "encryption.encrypt_modal.description_folder",
            "The folder and everything inside will be encrypted end-to-end. Only people you share it with will be able to access its contents.",
          )
        : t(
            "encryption.encrypt_modal.description_file",
            "The file will be encrypted end-to-end. Only people you share it with will be able to access its contents.",
          )
      : undefined;

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      closeOnClickOutside={!busy}
      size={ModalSize.MEDIUM}
      aria-label={title}
    >
      <EncryptionModalContent
        illustration="document-shield-check"
        title={title}
        description={description}
        actions={
          <>
            {job.phase === "ready" && (
              <Button onClick={() => job.confirm()} disabled={!job.canConfirm}>
                {intoChainParentId
                  ? t(
                      "encryption.encrypt_modal.confirm_into_chain",
                      "Encrypt & move",
                    )
                  : t("encryption.encrypt_modal.confirm", "Encrypt")}
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
        {job.pendingUserCount > 0 &&
          (job.phase === "ready" || job.phase === "validating") && (
            <Alert type={VariantType.WARNING}>
              {t(
                "encryption.encrypt_modal.pending_users",
                "{{count}} collaborator(s) have not enabled encryption yet. They will see this item but cannot open it until they do and someone accepts them from the share dialog.",
                { count: job.pendingUserCount },
              )}
            </Alert>
          )}

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
          mode="encrypt"
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
              "encryption.encrypt_modal.large_set",
              "{{count}} items in this folder. Per-item progress is hidden for large jobs — see the summary above.",
              { count: job.rows.length },
            )}
            {job.failedCount > 0 &&
              " " +
                t(
                  "encryption.encrypt_modal.large_set_failures",
                  "{{count}} failed.",
                  { count: job.failedCount },
                )}
          </p>
        )}
      </EncryptionModalContent>
    </Modal>
  );
};
