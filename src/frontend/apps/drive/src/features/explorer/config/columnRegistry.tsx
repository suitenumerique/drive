import { ColumnConfig, ColumnType } from "../types/columns";
import { LastModifiedCell } from "../components/embedded-explorer/cells/LastModifiedCell";
import { CreatedCell } from "../components/embedded-explorer/cells/CreatedCell";
import { CreatedByCell } from "../components/embedded-explorer/cells/CreatedByCell";
import { FileTypeCell } from "../components/embedded-explorer/cells/FileTypeCell";
import { FileSizeCell } from "../components/embedded-explorer/cells/FileSizeCell";
import { ClockIcon } from "@/features/ui/components/icon/Clock";
import { PersonIcon } from "@/features/ui/components/icon/PersoIcon";
import { FileIcon } from "@/features/ui/components/icon/FileIcon";
import { WeightIcon } from "@/features/ui/components/icon/WeightIcon";

export const COLUMN_REGISTRY: Record<ColumnType, ColumnConfig> = {
  [ColumnType.LAST_MODIFIED]: {
    type: ColumnType.LAST_MODIFIED,
    labelKey: "explorer.grid.columns.last_modified",
    icon: ClockIcon,
    orderingField: "updated_at",
    cell: LastModifiedCell,
  },
  [ColumnType.CREATED]: {
    type: ColumnType.CREATED,
    labelKey: "explorer.grid.columns.created",
    icon: ClockIcon,
    orderingField: "created_at",
    cell: CreatedCell,
  },
  [ColumnType.CREATED_BY]: {
    type: ColumnType.CREATED_BY,
    labelKey: "explorer.grid.columns.created_by",
    icon: PersonIcon,
    orderingField: "creator__full_name",
    cell: CreatedByCell,
  },
  [ColumnType.FILE_TYPE]: {
    type: ColumnType.FILE_TYPE,
    labelKey: "explorer.grid.columns.file_type",
    icon: FileIcon,
    orderingField: "mime_category",
    cell: FileTypeCell,
  },
  [ColumnType.FILE_SIZE]: {
    type: ColumnType.FILE_SIZE,
    labelKey: "explorer.grid.columns.file_size",
    icon: WeightIcon,
    orderingField: "size",
    cell: FileSizeCell,
  },
};
