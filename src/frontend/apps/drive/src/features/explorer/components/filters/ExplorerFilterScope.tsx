import { Filter, FilterOption } from "@gouvfr-lasuite/ui-kit";
import { useMemo } from "react";
import { useTranslation } from "react-i18next";
import { Key } from "react-aria-components";
import { ItemFiltersScope } from "@/features/drivers/Driver";
import { getResetOption } from "./filterUtils";

export const ExplorerFilterScope = (props: {
  value: string | null;
  onChange: (value: Key | null) => void;
}) => {
  const { t } = useTranslation();

  const options: FilterOption[] = useMemo(
    () => [
      {
        label: t("explorer.filters.scopes.options.trash"),
        value: ItemFiltersScope.DELETED,
        render: () => (
          <div className="explorer__filters__item">
            {t("explorer.filters.scopes.options.trash")}
          </div>
        ),
        showSeparator: true,
      },
      getResetOption(t),
    ],
    [t],
  );

  return (
    <Filter
      label={t("explorer.filters.scopes.label")}
      options={options}
      selectedKey={props.value ?? null} // undefined would trigger "uncontrolled components become controlled" warning.
      onSelectionChange={props.onChange}
    />
  );
};
