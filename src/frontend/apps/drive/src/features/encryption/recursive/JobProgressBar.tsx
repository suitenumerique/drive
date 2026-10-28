import { Tooltip } from "@gouvfr-lasuite/ui-components";
import { CSSProperties } from "react";
import { useTranslation } from "react-i18next";
import { RESTED_TOOLTIP_CLASS, RestedTooltipText } from "./RestedTooltipText";
import { JobPhase } from "./types";

type Props = {
  phase: JobPhase;
  total: number;
  done: number;
  mode: "encrypt" | "decrypt";
};

/**
 * The job's progress above its list, as a bare bar. The count it stands for
 * shows in a tooltip once the pointer rests on it, and is the bar's value for
 * assistive technologies. Shown from before the job starts, empty, so the
 * list does not move when it does.
 */
export const JobProgressBar = ({ phase, total, done, mode }: Props) => {
  const { t } = useTranslation();

  const started =
    phase !== "discovering" && phase !== "validating" && phase !== "ready";
  const finished = phase === "committing" || phase === "success";
  const value = finished ? total : started ? done : 0;
  const ratio = total > 0 ? value / total : finished ? 1 : 0;

  const label = !started
    ? mode === "encrypt"
      ? t("encryption.progress.to_encrypt", {
          count: total,
          defaultValue_one: "{{count}} item to encrypt",
          defaultValue_other: "{{count}} items to encrypt",
        })
      : t("encryption.progress.to_decrypt", {
          count: total,
          defaultValue_one: "{{count}} item to decrypt",
          defaultValue_other: "{{count}} items to decrypt",
        })
    : phase === "committing"
      ? t("encryption.progress.committing", "Finalizing…")
      : mode === "encrypt"
        ? t("encryption.progress.encrypted", {
            count: total,
            done: value,
            defaultValue_one: "{{done}} of {{count}} item encrypted",
            defaultValue_other: "{{done}} of {{count}} items encrypted",
          })
        : t("encryption.progress.decrypted", {
            count: total,
            done: value,
            defaultValue_one: "{{done}} of {{count}} item decrypted",
            defaultValue_other: "{{done}} of {{count}} items decrypted",
          });

  return (
    <Tooltip
      content={<RestedTooltipText text={label} />}
      placement="top"
      className={RESTED_TOOLTIP_CLASS}
    >
      <div
        className="drive__encryption-job-progress"
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={total}
        aria-valuenow={value}
        aria-valuetext={label}
      >
        <div
          className="drive__encryption-job-progress__track"
          style={{ "--progress": ratio } as CSSProperties}
        />
      </div>
    </Tooltip>
  );
};
