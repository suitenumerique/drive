import { useEffect, useState } from "react";
import {
  Button,
  Modal,
  ModalSize,
} from "@gouvfr-lasuite/ui-components";
import { useTranslation } from "react-i18next";
import { Item } from "@/features/drivers/types";
import { formatSize } from "@/features/explorer/utils/utils";

type NameConflictModalProps = {
  isOpen: boolean;
  filename: string;
  copyName: string;
  matches: Item[];
  onVersion: (itemId: string) => void;
  onCopy: () => void;
  onCancel: () => void;
};

export const NameConflictModal = ({
  isOpen,
  filename,
  copyName,
  matches,
  onVersion,
  onCopy,
  onCancel,
}: NameConflictModalProps) => {
  const { t } = useTranslation();
  const [selectedId, setSelectedId] = useState(matches[0]?.id ?? "");

  useEffect(() => {
    setSelectedId(matches[0]?.id ?? "");
  }, [matches]);

  const selected = matches.find((match) => match.id === selectedId) ?? matches[0];
  const canVersion = Boolean(selected?.abilities?.versions_restore);
  const descriptionKey =
    matches.length > 1
      ? "explorer.versions.name_conflict.description_multiple"
      : "explorer.versions.name_conflict.description";

  return (
    <Modal
      isOpen={isOpen}
      onClose={onCancel}
      title={t("explorer.versions.name_conflict.title")}
      size={ModalSize.MEDIUM}
      rightActions={
        <>
          <Button variant="bordered" onClick={onCancel}>
            {t("explorer.versions.name_conflict.cancel")}
          </Button>
          <Button variant="bordered" onClick={onCopy}>
            {t("explorer.versions.name_conflict.copy", { name: copyName })}
          </Button>
          <Button
            onClick={() => selected && onVersion(selected.id)}
            disabled={!canVersion || !selected}
          >
            {t("explorer.versions.name_conflict.version")}
          </Button>
        </>
      }
    >
      <div className="c__modal__content__text">
        {t(descriptionKey, { name: filename, copyName, count: matches.length })}
      </div>
      {matches.length > 1 && (
        <ul className="name-conflict__matches">
          {matches.map((match) => (
            <li key={match.id}>
              <label>
                <input
                  type="radio"
                  name="name-conflict-target"
                  checked={match.id === selected?.id}
                  onChange={() => setSelectedId(match.id)}
                />
                <span>
                  {match.updated_at.toLocaleString()}
                  {typeof match.size === "number" &&
                    ` · ${formatSize(match.size, t)}`}
                </span>
              </label>
            </li>
          ))}
        </ul>
      )}
    </Modal>
  );
};
