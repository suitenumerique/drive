import { ItemFilters } from "@/features/drivers/Driver";
import { TFunction } from "i18next";
import { Key } from "react-aria-components";

export const ALL = "all";

export const handleFilterChange = (
  filters: ItemFilters = {},
  name: string,
  value: Key | null,
) => {
  if (value === ALL) {
    const newFilters = { ...filters };
    delete newFilters[name as keyof ItemFilters];
    return newFilters;
  } else {
    return { ...filters, [name]: value };
  }
};

export const getResetOption = (t: TFunction) => {
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
