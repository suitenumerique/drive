import { ItemTreeItem } from "@/features/drivers/types";
import { FolderTreeIcon } from "@/features/ui/components/icon/Icon";

type ExplorerTreeItemProps = {
  item: ItemTreeItem;
};

export const ExplorerTreeItem = ({ item }: ExplorerTreeItemProps) => {
  return (
    <div className="explorer__tree__item">
      <FolderTreeIcon />
      <span className="explorer__tree__item__title">{item.title}</span>
    </div>
  );
};
