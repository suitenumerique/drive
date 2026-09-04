import {
  Filter,
  FilterOption,
  IconProps,
  IconSize,
} from "@gouvfr-lasuite/ui-components";
import { JSX, useMemo } from "react";
import { useTranslation } from "react-i18next";
import { Key } from "react-aria-components";
import { MyFilesIcon } from "@/features/ui/components/icon/MyFilesIcon";
import { SharedWithMeIcon } from "@/features/ui/components/icon/SharedWithMeIcon";
import { StarredIcon } from "@/features/ui/components/icon/StarredIcon";
import { TrashIcon } from "@/features/ui/components/icon/TrashIcon";

const LOCATION_OPTIONS: {
  value: string;
  icon: (props: Partial<IconProps>) => JSX.Element;
}[] = [
  { value: "my_files", icon: MyFilesIcon },
  { value: "shared_with_me", icon: SharedWithMeIcon },
  { value: "starred", icon: StarredIcon },
  { value: "trashbin", icon: TrashIcon },
];

export const ExplorerFilterLocation = (props: {
  value: string | null;
  onChange: (value: Key | null) => void;
}) => {
  const { t } = useTranslation();

  const options: FilterOption[] = useMemo(
    () => [
      ...LOCATION_OPTIONS.map(({ value, icon: Icon }) => ({
        label: t(`explorer.filters.location.options.${value}`),
        value,
        render: () => (
          <div className="explorer__filters__item">
            <Icon size={IconSize.SMALL} />
            {t(`explorer.filters.location.options.${value}`)}
          </div>
        ),
      })),
    ],
    [t],
  );

  return (
    <Filter
      label={t("explorer.filters.location.label")}
      options={options}
      selectedKey={props.value ?? null} // undefined would trigger "uncontrolled components become controlled" warning.
      onSelectionChange={props.onChange}
    />
  );
};
