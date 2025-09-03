import { Filter, FilterOption, IconSize } from "@gouvfr-lasuite/ui-kit";
import { useMemo } from "react";
import { useTranslation } from "react-i18next";
import folderIcon from "@/assets/folder/folder.svg";
import mimeOther from "@/assets/files/icons/mime-other.svg";
import { Key } from "react-aria-components";
import { useAppExplorer } from "./AppExplorer";
import { ItemType } from "@/features/drivers/types";
import { ItemFilters } from "@/features/drivers/Driver";
import { useFirstLevelItems } from "../../hooks/useQueries";
import { TFunction } from "i18next";
import { ItemIcon } from "../icons/ItemIcon";
import { getItemTitle } from "../../utils/utils";

const ALL = "all";

export const handleFilterChange = (
  filters: ItemFilters = {},
  name: string,
  value: Key | null
) => {
  if (value === ALL) {
    const newFilters = { ...filters };
    delete newFilters[name as keyof ItemFilters];
    return newFilters;
  } else {
    return { ...filters, [name]: value };
  }
};

const getResetOption = (t: TFunction) => {
  return {
    label: t("explorer.filters.type.options.reset"),
    render: () => (
      <div className="explorer__filters__item">
        <span className="material-icons">undo</span>
        {t("explorer.filters.type.options.reset")}
      </div>
    ),
    value: ALL,
  };
};

export const ExplorerFilters = () => {
  const { filters, onFiltersChange } = useAppExplorer();

  const onChange = (name: string, value: Key | null) => {
    onFiltersChange?.(handleFilterChange(filters, name, value));
  };

  return (
    <div className="explorer__filters">
      <ExplorerFilterType
        value={filters?.type ?? null}
        onChange={(value) => onChange("type", value)}
      />
    </div>
  );
};

export const ExplorerFilterType = (props: {
  value: ItemType | null;
  onChange: (value: Key | null) => void;
}) => {
  const { t } = useTranslation();

  const typeOptions: FilterOption[] = useMemo(
    () => [
      {
        label: t("explorer.filters.type.options.folder"),
        value: "folder",
        render: () => (
          <div className="explorer__filters__item">
            <img src={folderIcon.src} alt="" width="24" height="24" />
            {t("explorer.filters.type.options.folder")}
          </div>
        ),
      },
      {
        label: t("explorer.filters.type.options.file"),
        render: () => (
          <div className="explorer__filters__item">
            <img src={mimeOther.src} alt="" width="24" height="24" />
            {t("explorer.filters.type.options.file")}
          </div>
        ),
        value: "file",
        showSeparator: true,
      },
      getResetOption(t),
    ],
    [t]
  );

  return (
    <Filter
      label={t("explorer.filters.type.label")}
      options={typeOptions}
      selectedKey={props.value ?? null} // undefined would trigger "uncontrolled components become controlled" warning.
      onSelectionChange={props.onChange}
    />
  );
};

export const ExplorerFilterWorkspace = (props: {
  value: string | null;
  onChange: (value: Key | null) => void;
}) => {
  const { t } = useTranslation();
  const { data: firstLevelItems } = useFirstLevelItems();

  const options = useMemo(() => {
    return [
      ...(firstLevelItems?.map((item) => ({
        label: item.title,
        value: item.id,
        render: () => (
          <div className="explorer__filters__item">
            <ItemIcon item={item} size={IconSize.SMALL} />
            {getItemTitle(item)}
          </div>
        ),
      })) ?? []),
      getResetOption(t),
    ];
  }, [firstLevelItems]);

  if (!options) {
    return null;
  }

  return (
    <Filter
      label={t("explorer.filters.workspace.label")}
      options={options}
      selectedKey={props.value ?? null} // undefined would trigger "uncontrolled components become controlled" warning.
      onSelectionChange={props.onChange}
    />
  );
};
