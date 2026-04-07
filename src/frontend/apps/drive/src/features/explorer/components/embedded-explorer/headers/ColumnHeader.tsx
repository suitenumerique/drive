import { SortState } from "@/features/explorer/types/columns";
import { SortColumnButton } from "./SortColumnButton";

type SortColumnId = NonNullable<SortState>["columnId"];

export type ColumnHeaderProps = {
  label: string;
  columnId: SortColumnId;
  sortState: SortState;
  onSort: (columnId: SortColumnId) => void;
  sortable?: boolean;
};

export const ColumnHeader = ({
  label,
  columnId,
  sortState,
  onSort,
  sortable = true,
}: ColumnHeaderProps) => {
  return (
    <div className="c__datagrid__header fs-h5 c__datagrid__header--sortable explorer__grid__header">
      <span className="explorer__grid__header__label">{label}</span>
      {sortable && (
        <SortColumnButton columnId={columnId} sortState={sortState} onSort={onSort} />
      )}
    </div>
  );
};
