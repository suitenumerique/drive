import { Filter } from "@gouvfr-lasuite/ui-kit";
import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import folderIcon from "@/assets/folder/folder.svg";
import mimeOther from "@/assets/files/icons/mime-other.svg";
import { Key } from "react-aria-components";
import { useExplorerInner } from "./Explorer";
import { ItemType } from "@/features/drivers/types";

export const ExplorerFilters = () => {
  const { t } = useTranslation();

  const typeOptions = useMemo(
    () => [
      {
        label: t("explorer.filters.type.options.all"),
        render: () => (
          <div style={{ display: "flex", alignItems: "center", gap: "0.5em" }}>
            <span className="material-icons">check</span>
            {t("explorer.filters.type.options.all")}
          </div>
        ),
        value: "all",
      },
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
      },
    ],
    [t]
  );

  const { filters, onFiltersChange } = useExplorerInner();

  const onTypeChange = (value: Key) => {
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
