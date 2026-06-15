import { Filter, IconSize } from "@gouvfr-lasuite/ui-kit";
import { useMemo } from "react";
import { useTranslation } from "react-i18next";
import { Key } from "react-aria-components";
import { useItems } from "@/features/explorer/hooks/useQueries";
import { ItemIcon } from "@/features/explorer/components/icons/ItemIcon";
import { getItemTitle } from "@/features/explorer/utils/utils";
import { getResetOption } from "./filterUtils";

export const ExplorerFilterWorkspace = (props: {
  value: string | null;
  onChange: (value: Key | null) => void;
  isDisabled?: boolean;
}) => {
  const { t } = useTranslation();
  const { data: items } = useItems();

  const options = useMemo(() => {
    return [
      ...(items?.map((item) => ({
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
  }, [items]);

  if (!options) {
    return null;
  }

  return (
    <Filter
      label={t("explorer.filters.folders.label")}
      options={options}
      selectedKey={props.value ?? null} // undefined would trigger "uncontrolled components become controlled" warning.
      onSelectionChange={props.onChange}
      isDisabled={props.isDisabled}
    />
  );
};
