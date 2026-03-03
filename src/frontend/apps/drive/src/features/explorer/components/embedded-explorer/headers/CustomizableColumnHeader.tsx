import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "@gouvfr-lasuite/cunningham-react";
import { DropdownMenu, IconSize, MenuItem } from "@gouvfr-lasuite/ui-kit";
import { ColumnType, SortState } from "@/features/explorer/types/columns";
import { COLUMN_REGISTRY } from "@/features/explorer/config/columnRegistry";
import { SortColumnButton } from "./SortColumnButton";

export type CustomizableColumnHeaderProps = {
  slot: "column1" | "column2";
  currentType: ColumnType;
  defaultType: ColumnType;
  sortState: SortState;
  onSort: (columnId: ColumnType) => void;
  onChangeColumn: (type: ColumnType) => void;
};

const ALL_COLUMN_TYPES = Object.values(ColumnType);

export const CustomizableColumnHeader = ({
  currentType,
  defaultType,
  sortState,
  onSort,
  onChangeColumn,
}: CustomizableColumnHeaderProps) => {
  const { t } = useTranslation();
  const [isOpen, setIsOpen] = useState(false);

  const currentConfig = COLUMN_REGISTRY[currentType];
  const IconComponent = currentConfig.icon;
  const buttonIcon = <IconComponent size={IconSize.SMALL} />;

  const dropdownOptions = useMemo<MenuItem[]>(
    () =>
      ALL_COLUMN_TYPES.flatMap((type) => {
        const config = COLUMN_REGISTRY[type];
        const isDefault = type === defaultType;
        const label = isDefault
          ? `${t(config.labelKey)} ${t("explorer.grid.columns.default_suffix")}`
          : t(config.labelKey);

        const Icon = config.icon;
        const result = {
          icon: <Icon />,
          label,
          value: type,
          callback: () => {
            onChangeColumn(type);
          },
        };

        if (type === ColumnType.CREATED_BY) {
          return [{ type: "separator" }, result, { type: "separator" }];
        }

        return [result];
      }),
    [defaultType, t, onChangeColumn],
  );

  return (
    <div className="c__datagrid__header fs-h5 c__datagrid__header--sortable explorer__grid__header">
      <DropdownMenu
        options={dropdownOptions}
        isOpen={isOpen}
        onOpenChange={setIsOpen}
      >
        <Button
          color="neutral"
          variant="tertiary"
          size="nano"
          icon={buttonIcon}
          onClick={() => setIsOpen(!isOpen)}
        >
          {t(currentConfig.labelKey)}
        </Button>
      </DropdownMenu>
      {currentConfig.sortable !== false && (
        <SortColumnButton
          columnId={currentType}
          sortState={sortState}
          onSort={onSort}
        />
      )}
    </div>
  );
};
