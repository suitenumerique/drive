import { SortState } from "@/features/explorer/types/columns";
import { SortColumnButton } from "./SortColumnButton";

type SortColumnId = NonNullable<SortState>["columnId"];

export type SortableColumnHeaderProps = {
  label: string;
  columnId: SortColumnId;
  sortState: SortState;
  onSort: (columnId: SortColumnId) => void;
};

export const SortableColumnHeader = ({
  label,
  columnId,
  sortState,
  onSort,
}: SortableColumnHeaderProps) => {
  return (
    <div className="c__datagrid__header fs-h5 c__datagrid__header--sortable explorer__grid__header">
      <span className="explorer__grid__header__label">{label}</span>
      <SortColumnButton columnId={columnId} sortState={sortState} onSort={onSort} />
    </div>
  );
};
