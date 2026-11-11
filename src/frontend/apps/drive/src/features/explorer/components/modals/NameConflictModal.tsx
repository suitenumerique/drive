import { useEffect, useState } from "react";
import { Button, Modal, ModalSize } from "@gouvfr-lasuite/ui-components";
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
  const [choice, setChoice] = useState<"version" | "copy">("copy");
  const [selectedId, setSelectedId] = useState(matches[0]?.id ?? "");

  useEffect(() => {
    setChoice("copy");
    setSelectedId(matches[0]?.id ?? "");
  }, [matches, filename]);

  const selected = matches.find((match) => match.id === selectedId) ?? matches[0];
  const canVersion = Boolean(selected?.abilities?.versions_restore);

  const importChoice = () => {
    if (choice === "version" && selected && canVersion) {
      onVersion(selected.id);
      return;
    }
    onCopy();
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onCancel}
      title={t("explorer.versions.name_conflict.title")}
      subtitle={t("explorer.versions.name_conflict.subtitle", { name: filename })}
      size={ModalSize.MEDIUM}
      rightActions={
        <>
          <Button variant="bordered" onClick={onCancel}>
            {t("explorer.versions.name_conflict.cancel")}
          </Button>
          <Button
            onClick={importChoice}
            disabled={choice === "version" && !canVersion}
          >
            {t("explorer.versions.name_conflict.import")}
          </Button>
        </>
      }
    >
      <div className="name-conflict" role="radiogroup">
        <label className="name-conflict__option">
          <input
            type="radio"
            name="name-conflict-action"
            checked={choice === "version"}
            disabled={!canVersion}
            onChange={() => setChoice("version")}
          />
          <span>
            <span className="name-conflict__label">
              {t("explorer.versions.name_conflict.replace")}
            </span>
            <span className="name-conflict__hint">
              {t("explorer.versions.name_conflict.replace_hint")}
            </span>
          </span>
        </label>
        {choice === "version" && matches.length > 1 && (
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
                    {match.title}
                    {" · "}
                    {match.updated_at.toLocaleString()}
                    {typeof match.size === "number" &&
                      ` · ${formatSize(match.size, t)}`}
                  </span>
                </label>
              </li>
            ))}
          </ul>
        )}
        <label className="name-conflict__option">
          <input
            type="radio"
            name="name-conflict-action"
            checked={choice === "copy"}
            onChange={() => setChoice("copy")}
          />
          <span>
            <span className="name-conflict__label">
              {t("explorer.versions.name_conflict.keep", { name: copyName })}
            </span>
            <span className="name-conflict__hint">
              {t("explorer.versions.name_conflict.keep_hint", { name: copyName })}
            </span>
          </span>
        </label>
      </div>
    </Modal>
  );
};
