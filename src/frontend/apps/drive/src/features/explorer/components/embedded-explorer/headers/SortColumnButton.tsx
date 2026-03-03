import { useTranslation } from "react-i18next";
import { Button, Tooltip } from "@gouvfr-lasuite/cunningham-react";
import { IconSize } from "@gouvfr-lasuite/ui-kit";
import { SortState } from "@/features/explorer/types/columns";
import { SortAscIcon } from "@/features/ui/components/icon/sorting/sort-asc";
import { SortDescIcon } from "@/features/ui/components/icon/sorting/sort-desc";
import { SortNeutralIcon } from "@/features/ui/components/icon/sorting/sort-neutral";

type SortColumnId = NonNullable<SortState>["columnId"];

type SortColumnButtonProps<TColumnId extends SortColumnId> = {
  columnId: TColumnId;
  sortState: SortState;
  onSort: (columnId: TColumnId) => void;
};

export const SortColumnButton = <TColumnId extends SortColumnId>({
  columnId,
  sortState,
  onSort,
}: SortColumnButtonProps<TColumnId>) => {
  const { t } = useTranslation();

  const isActive = sortState?.columnId === columnId;
  const direction = isActive ? sortState.direction : null;

  const nextTooltip = (() => {
    if (!isActive) return t("explorer.grid.sort.ascending");
    if (direction === "asc") return t("explorer.grid.sort.descending");
    return t("explorer.grid.sort.reset");
  })();

  const sortIcon = (() => {
    if (!isActive) return <SortNeutralIcon size={IconSize.SMALL} />;
    if (direction === "asc") return <SortAscIcon size={IconSize.SMALL} />;
    return <SortDescIcon size={IconSize.SMALL} />;
  })();

  return (
    <Tooltip content={nextTooltip}>
      <Button
        color={isActive ? "brand" : "neutral"}
        size="nano"
        variant={isActive ? "secondary" : "tertiary"}
        icon={sortIcon}
        onClick={(e) => {
          e.stopPropagation();
          onSort(columnId);
        }}
        aria-label={nextTooltip}
      />
    </Tooltip>
  );
};
