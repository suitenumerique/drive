import { Item, TreeItem } from "@/features/drivers/types";
import {
  TreeViewDataType,
  TreeViewNodeTypeEnum,
  useTreeContext,
} from "@gouvfr-lasuite/ui-kit";
import { useTranslation } from "react-i18next";
import { itemToTreeItem } from "../../ExplorerContext";

export const useAddWorkspaceNode = () => {
  const treeContext = useTreeContext<TreeItem>();
  const { t } = useTranslation();
  const addWorkspaceNode = (data: Item) => {
    const items = treeContext?.treeData.nodes.map((node) => node.value) ?? [];
    if (items.length === 2) {
      const separator: TreeViewDataType<TreeItem> = {
        id: "SEPARATOR",
        nodeType: TreeViewNodeTypeEnum.SEPARATOR,
      };

      const sharedSpace: TreeViewDataType<TreeItem> = {
        id: "SHARED_SPACE",
        nodeType: TreeViewNodeTypeEnum.TITLE,
        headerTitle: t("explorer.tree.sharedSpace"),
      };

      treeContext?.treeData.addRootNodes([
        separator,
        sharedSpace,
        itemToTreeItem(data),
      ]);
    } else {
      treeContext?.treeData.addRootNode(itemToTreeItem(data), 4);
    }
  };

  return { addWorkspaceNode };
};
