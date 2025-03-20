import { TreeViewNodeTypeEnum } from "@gouvfr-lasuite/ui-kit";

export enum ItemType {
  FILE = "file",
  FOLDER = "folder",
}

export type Item = {
  id: string;
  title: string;
  type: ItemType;
  upload_state: string;
  updated_at: Date;
  children?: Item[];
  numchild?: number;
  numchild_folder?: number;
  path: string;
  url?: string;
  policy?: {
    url: string;
    fields: {
      AWSAccessKeyId: string;
      acl: string;
      policy: string;
      key: string;
      signature: string;
    };
  };
};

export type ItemTreeItem = Omit<Item, "children"> & {
  childrenCount?: number;
  children?: ItemTreeItem[];
  nodeType: TreeViewNodeTypeEnum;
  parentId?: string;
};
