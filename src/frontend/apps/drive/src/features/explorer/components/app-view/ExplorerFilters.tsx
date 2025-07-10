import { Filter, FilterOption } from "@gouvfr-lasuite/ui-kit";
import { useMemo } from "react";
import { useTranslation } from "react-i18next";
import folderIcon from "@/assets/folder/folder.svg";
import mimeOther from "@/assets/files/icons/mime-other.svg";
import { Key } from "react-aria-components";
import { useAppExplorer } from "./AppExplorer";
import { ItemType } from "@/features/drivers/types";

export const ExplorerFilters = () => {
  const { t } = useTranslation();

  const typeOptions: FilterOption[] = useMemo(
    () => [
      {
        label: t("explorer.filters.type.options.folder"),
        value: "folder",
        render: () => (
          <div style={{ display: "flex", alignItems: "center", gap: "0.5em" }}>
            <img src={folderIcon.src} alt="" width="24" height="24" />
            {t("explorer.filters.type.options.folder")}
          </div>
        ),
      },
      {
        label: t("explorer.filters.type.options.file"),
        render: () => (
          <div style={{ display: "flex", alignItems: "center", gap: "0.5em" }}>
            <img src={mimeOther.src} alt="" width="24" height="24" />
            {t("explorer.filters.type.options.file")}
          </div>
        ),
        value: "file",
        showSeparator: true,
      },
      {
        label: t("explorer.filters.type.options.reset"),
        render: () => (
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "0.5em",
            }}
          >
            <span className="material-icons">undo</span>
            {t("explorer.filters.type.options.reset")}
          </div>
        ),
        value: "all",
      },
    ],
    [t]
  );

  const { filters, onFiltersChange } = useAppExplorer();

  const onTypeChange = (value: Key | null) => {
    if (value === "all") {
      const newFilters = { ...filters };
      delete newFilters.type;
      onFiltersChange?.(newFilters);
    } else {
      onFiltersChange?.({ type: value as ItemType });
    }
  };

  return (
    <div className="explorer__filters">
      <Filter
        label={t("explorer.filters.type.label")}
        options={typeOptions}
        selectedKey={filters?.type ?? null} // undefined would trigger "uncontrolled components become controlled" warning.
        onSelectionChange={onTypeChange}
      />
    </div>
  );
};
