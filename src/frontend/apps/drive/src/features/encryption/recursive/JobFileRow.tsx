import { IconSize, Tooltip } from "@gouvfr-lasuite/ui-components";
import {
  Circle,
  CircleCheckFilled,
  Error as ErrorIcon,
  Loader,
} from "@gouvfr-lasuite/ui-components/icons";
import clsx from "clsx";
import { useLayoutEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { ItemIcon } from "@/features/explorer/components/icons/ItemIcon";
import { ItemType } from "@/features/drivers/types";
import { formatSize } from "@/features/explorer/utils/utils";
import { RESTED_TOOLTIP_CLASS, RestedTooltipText } from "./RestedTooltipText";
import { FileJobRow } from "./types";

/**
 * Whether the one-line text in a cell is cut by its ellipsis. Measured on the
 * text itself against its box, both unrounded: scrollWidth and clientWidth
 * round to whole pixels, so a text overflowing by less than one would measure
 * as fitting. Read from the cell, which stays in place when the text gets its
 * tooltip (the tooltip takes the text's own ref).
 */
export const useIsCut = (text: string) => {
  const ref = useRef<HTMLDivElement>(null);
  const [isCut, setIsCut] = useState(false);

  useLayoutEffect(() => {
    const cell = ref.current;
    if (!cell) return;

    const measure = () => {
      const element = cell.firstElementChild;
      if (!element) return;
      const range = document.createRange();
      range.selectNodeContents(element);
      setIsCut(
        range.getBoundingClientRect().width >
          element.getBoundingClientRect().width,
      );
    };
    const observer = new ResizeObserver(measure);

    measure();
    observer.observe(cell);
    return () => observer.disconnect();
  }, [text]);

  return { ref, isCut };
};

/**
 * One item of an encryption job, laid out as the upload list's row: icon,
 * name, size, and the item's state at the end. Every state has its icon, so
 * the row does not shift when the item starts.
 */
export const JobFileRow = ({
  row,
  mode,
}: {
  row: FileJobRow;
  mode: "encrypt" | "decrypt";
}) => {
  const { t } = useTranslation();
  const isRunning = row.state === "running";

  const name = isRunning
    ? mode === "encrypt"
      ? t("encryption.row.encrypting", "{{title}}: encrypting", {
          title: row.title,
        })
      : t("encryption.row.decrypting", "{{title}}: decrypting", {
          title: row.title,
        })
    : row.title;
  const { ref: nameCellRef, isCut } = useIsCut(name);

  const detail =
    row.state === "skipped"
      ? row.skipReason === "not_encrypted"
        ? t("encryption.row.not_encrypted", "Not encrypted")
        : t("encryption.row.already_encrypted", "Already encrypted")
      : row.item.type === ItemType.FILE && row.item.size != null
        ? formatSize(row.item.size, t)
        : null;

  const status = (() => {
    switch (row.state) {
      case "pending":
        return <Circle size={IconSize.SMALL} aria-hidden />;
      case "running":
        return (
          <Loader
            size={IconSize.SMALL}
            className="drive__encryption-spin"
            aria-hidden
          />
        );
      // Already in the target state: nothing to do, shown as done but muted.
      case "skipped":
      case "staged":
      case "done":
        return <CircleCheckFilled size={IconSize.SMALL} aria-hidden />;
      case "failed": {
        // The cause is technical and untranslated (a status code, a vault
        // error): framed by a sentence in the user's language.
        const failure = t(
          "encryption.row.failed",
          "Could not be processed ({{error}})",
          { error: row.error },
        );
        return (
          <Tooltip content={failure}>
            <span>
              <ErrorIcon size={IconSize.SMALL} aria-label={failure} />
            </span>
          </Tooltip>
        );
      }
    }
  })();

  const nameElement = <p className="drive__encryption-job-row__name">{name}</p>;

  return (
    <div
      className={clsx(
        "drive__encryption-job-row",
        `drive__encryption-job-row--${row.state}`,
      )}
    >
      <ItemIcon item={row.item} size={IconSize.LARGE} />
      <div ref={nameCellRef} className="drive__encryption-job-row__name-cell">
        {isCut ? (
          <Tooltip
            content={<RestedTooltipText text={name} />}
            placement="top"
            className={RESTED_TOOLTIP_CLASS}
          >
            {nameElement}
          </Tooltip>
        ) : (
          nameElement
        )}
      </div>
      {detail && <p className="drive__encryption-job-row__detail">{detail}</p>}
      <span className="drive__encryption-job-row__status">{status}</span>
    </div>
  );
};
