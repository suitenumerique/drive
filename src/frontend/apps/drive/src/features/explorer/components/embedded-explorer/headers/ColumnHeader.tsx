import { SortState } from "@/features/explorer/types/columns";
import { SortColumnButton } from "./SortColumnButton";

type SortColumnId = NonNullable<SortState>["columnId"];

export type ColumnHeaderProps = {
  label: string;
  labelId: string;
  columnId: SortColumnId;
  sortState: SortState;
  onSort: (columnId: SortColumnId) => void;
  sortable?: boolean;
};

export const ColumnHeader = ({
  label,
  labelId,
  columnId,
  sortState,
  onSort,
  sortable = true,
}: ColumnHeaderProps) => {
  return (
    <div className="c__datagrid__header fs-h5 c__datagrid__header--sortable explorer__grid__header">
      <span id={labelId} className="explorer__grid__header__label">
        {label}
      </span>
      {sortable && (
        <SortColumnButton
          columnId={columnId}
          columnLabel={label}
          sortState={sortState}
          onSort={onSort}
        />
      )}
    </div>
  );
};
