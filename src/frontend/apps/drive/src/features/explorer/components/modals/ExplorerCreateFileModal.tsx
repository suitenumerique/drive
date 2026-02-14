import {
  Button,
  Modal,
  ModalProps,
  ModalSize,
} from "@gouvfr-lasuite/cunningham-react";
import { useTranslation } from "react-i18next";
import { useEffect, useMemo, useState } from "react";
import clsx from "clsx";
import { useMutationCreateNewFile } from "../../hooks/useMutations";
import { useGlobalExplorer } from "../GlobalExplorerContext";
import { useRouter } from "next/router";

type ExplorerCreateFileModalProps = Pick<ModalProps, "isOpen" | "onClose"> & {
  parentId?: string;
  canCreateChildren?: boolean;
};

type CreateKind = "text" | "sheet" | "slide";

type ExtensionOption = {
  ext: string;
  labelKey: string;
  isRecommended?: boolean;
};

const DEFAULT_EXTENSION_BY_KIND: Record<CreateKind, string> = {
  text: "odt",
  sheet: "ods",
  slide: "odp",
};

const EXTENSIONS_BY_KIND: Record<CreateKind, ExtensionOption[]> = {
  text: [
    { ext: "odt", labelKey: "odt", isRecommended: true },
    { ext: "docx", labelKey: "docx" },
    { ext: "doc", labelKey: "doc" },
    { ext: "rtf", labelKey: "rtf" },
    { ext: "txt", labelKey: "txt" },
    { ext: "md", labelKey: "md" },
    { ext: "sh", labelKey: "sh" },
    { ext: "ps1", labelKey: "ps1" },
  ],
  sheet: [
    { ext: "ods", labelKey: "ods", isRecommended: true },
    { ext: "xlsx", labelKey: "xlsx" },
    { ext: "xls", labelKey: "xls" },
    { ext: "csv", labelKey: "csv" },
    { ext: "tsv", labelKey: "tsv" },
  ],
  slide: [
    { ext: "odp", labelKey: "odp", isRecommended: true },
    { ext: "pptx", labelKey: "pptx" },
    { ext: "ppt", labelKey: "ppt" },
  ],
};

const getDefaultStemForKind = (kind: CreateKind, t: (key: string) => string) => {
  const legacyKey =
    kind === "text" ? "odt" : kind === "sheet" ? "ods" : "odp";
  const filename = t(`explorer.actions.createOdf.defaults.${legacyKey}`);
  const suffix = `.${legacyKey}`;
  return filename.endsWith(suffix) ? filename.slice(0, -suffix.length) : filename;
};

export const ExplorerCreateFileModal = ({
  canCreateChildren = true,
  ...props
}: ExplorerCreateFileModalProps) => {
  const { t } = useTranslation();
  const router = useRouter();
  const createNewFile = useMutationCreateNewFile();
  const { setPreviewItem, setPreviewItems } = useGlobalExplorer();

  const effectiveParentId = canCreateChildren ? props.parentId : undefined;

  const [kind, setKind] = useState<CreateKind>("text");
  const [extension, setExtension] = useState<string>(
    DEFAULT_EXTENSION_BY_KIND.text,
  );
  const [filenameStem, setFilenameStem] = useState<string>("");
  const [extensionSearch, setExtensionSearch] = useState<string>("");

  useEffect(() => {
    if (!props.isOpen) {
      return;
    }
    setKind("text");
    setExtension(DEFAULT_EXTENSION_BY_KIND.text);
    setFilenameStem(getDefaultStemForKind("text", t));
    setExtensionSearch("");
  }, [props.isOpen, t]);

  const options = useMemo(() => EXTENSIONS_BY_KIND[kind], [kind]);
  const filteredOptions = useMemo(() => {
    const q = extensionSearch.trim().toLowerCase();
    if (!q) {
      return options;
    }
    return options.filter((opt) => {
      const label = t(`explorer.actions.createFile.extensions.${opt.labelKey}`);
      return (
        opt.ext.includes(q) ||
        label.toLowerCase().includes(q) ||
        `.${opt.ext}`.includes(q)
      );
    });
  }, [extensionSearch, options, t]);

  const recommended = filteredOptions.filter((o) => o.isRecommended);
  const others = filteredOptions.filter((o) => !o.isRecommended);

  const canSubmit = filenameStem.trim().length > 0 && !createNewFile.isPending;

  const handleSubmit = () => {
    if (!canSubmit) {
      return;
    }

    createNewFile.mutate(
      {
        parentId: effectiveParentId,
        filenameStem,
        extension,
        kind,
      },
      {
        onSuccess: (created) => {
          setPreviewItems([created]);
          setPreviewItem(created);
          props.onClose();
          if (!effectiveParentId) {
            router.push(`/explorer/items/my-files`);
          }
        },
      },
    );
  };

  return (
    <Modal
      {...props}
      size={ModalSize.MEDIUM}
      title={t("explorer.actions.createFile.modal.title")}
      rightActions={
        <>
          <Button variant="bordered" onClick={props.onClose}>
            {t("common.cancel")}
          </Button>
          <Button onClick={handleSubmit} disabled={!canSubmit}>
            {t("explorer.actions.createFile.modal.submit")}
          </Button>
        </>
      }
    >
      <div className="explorer__create-file__modal">
        <div className="explorer__create-file__modal__field">
          <div className="explorer__create-file__modal__label">
            {t("explorer.actions.createFile.modal.filename_label")}
          </div>
          <div className="explorer__create-file__modal__filename-row">
            <input
              className="explorer__create-file__modal__filename-input"
              value={filenameStem}
              autoFocus={true}
              onChange={(e) => setFilenameStem(e.target.value)}
            />
            <div className="explorer__create-file__modal__extension-suffix">
              .{extension}
            </div>
          </div>
        </div>

        <div className="explorer__create-file__modal__columns">
          <div className="explorer__create-file__modal__column">
            <div className="explorer__create-file__modal__label">
              {t("explorer.actions.createFile.modal.kind_label")}
            </div>
            <div className="explorer__create-file__modal__list">
              {(["text", "sheet", "slide"] as const).map((k) => (
                <button
                  key={k}
                  type="button"
                  className={clsx("explorer__create-file__modal__row", {
                    selected: kind === k,
                  })}
                  onClick={() => {
                    setKind(k);
                    setExtension(DEFAULT_EXTENSION_BY_KIND[k]);
                    setExtensionSearch("");
                  }}
                >
                  {t(`explorer.actions.createFile.kinds.${k}`)}
                </button>
              ))}
            </div>
          </div>

          <div className="explorer__create-file__modal__column">
            <div className="explorer__create-file__modal__label">
              {t("explorer.actions.createFile.modal.extension_label")}
            </div>

            <div className="explorer__create-file__modal__search">
              <span className="material-icons">search</span>
              <input
                value={extensionSearch}
                onChange={(e) => setExtensionSearch(e.target.value)}
                placeholder={t("explorer.actions.createFile.modal.search_placeholder")}
              />
            </div>

            <div className="explorer__create-file__modal__list explorer__create-file__modal__list--scroll">
              {recommended.length > 0 && (
                <>
                  <div className="explorer__create-file__modal__section-title">
                    {t("explorer.actions.createFile.modal.recommended")}
                  </div>
                  {recommended.map((opt) => (
                    <button
                      key={opt.ext}
                      type="button"
                      className={clsx("explorer__create-file__modal__row", {
                        selected: extension === opt.ext,
                      })}
                      onClick={() => setExtension(opt.ext)}
                    >
                      <span className="explorer__create-file__modal__ext">
                        .{opt.ext}
                      </span>
                      <span className="explorer__create-file__modal__ext-label">
                        {t(
                          `explorer.actions.createFile.extensions.${opt.labelKey}`,
                        )}
                      </span>
                    </button>
                  ))}
                </>
              )}

              {others.length > 0 && (
                <>
                  <div className="explorer__create-file__modal__section-title">
                    {t("explorer.actions.createFile.modal.others")}
                  </div>
                  {others.map((opt) => (
                    <button
                      key={opt.ext}
                      type="button"
                      className={clsx("explorer__create-file__modal__row", {
                        selected: extension === opt.ext,
                      })}
                      onClick={() => setExtension(opt.ext)}
                    >
                      <span className="explorer__create-file__modal__ext">
                        .{opt.ext}
                      </span>
                      <span className="explorer__create-file__modal__ext-label">
                        {t(
                          `explorer.actions.createFile.extensions.${opt.labelKey}`,
                        )}
                      </span>
                    </button>
                  ))}
                </>
              )}
            </div>
          </div>
        </div>
      </div>
    </Modal>
  );
};
