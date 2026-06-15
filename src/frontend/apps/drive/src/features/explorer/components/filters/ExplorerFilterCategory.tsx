import { FileIcon, Filter, FilterOption, IconSize } from "@gouvfr-lasuite/ui-kit";
import { useMemo } from "react";
import { useTranslation } from "react-i18next";
import { Key } from "react-aria-components";
import { getResetOption } from "./filterUtils";

// A representative mimetype per category, resolved to an icon by the ui-kit's
// getMimeCategory so filter options match the icons shown on items.
const CATEGORY_OPTIONS: { value: string; mimetype: string }[] = [
  { value: "doc", mimetype: "application/vnd.oasis.opendocument.text" },
  { value: "powerpoint", mimetype: "application/vnd.oasis.opendocument.presentation" },
  { value: "calc", mimetype: "application/vnd.oasis.opendocument.spreadsheet" },
  { value: "pdf", mimetype: "application/pdf" },
  { value: "image", mimetype: "image/png" },
  { value: "video", mimetype: "video/mp4" },
  { value: "audio", mimetype: "audio/mpeg" },
  { value: "archive", mimetype: "application/zip" },
  { value: "other", mimetype: "text/plain" },
];

export const ExplorerFilterCategory = (props: {
  value: string | null;
  onChange: (value: Key | null) => void;
}) => {
  const { t } = useTranslation();

  const options: FilterOption[] = useMemo(
    () => [
      // Reset sits at the top of the list, above the categories, as in the design.
      { ...getResetOption(t), showSeparator: true },
      ...CATEGORY_OPTIONS.map(({ value, mimetype }) => ({
        label: t(`explorer.filters.category.options.${value}`),
        value,
        render: () => (
          <div className="explorer__filters__item">
            <FileIcon file={{ mimetype, title: "" }} size={IconSize.SMALL} />
            {t(`explorer.filters.category.options.${value}`)}
          </div>
        ),
      })),
    ],
    [t],
  );

  return (
    <Filter
      label={t("explorer.filters.category.label")}
      options={options}
      selectedKey={props.value ?? null} // undefined would trigger "uncontrolled components become controlled" warning.
      onSelectionChange={props.onChange}
    />
  );
};
