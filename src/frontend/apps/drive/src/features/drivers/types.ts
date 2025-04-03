import { TreeViewDataType } from "@gouvfr-lasuite/ui-kit";

export enum ItemType {
  FILE = "file",
  FOLDER = "folder",
}

export type Item = {
  id: string;
  title: string;
  filename: string;
  creator: string;
  type: ItemType;
  upload_state: string;
  updated_at: Date;
  description: string;
  created_at: Date;
  children?: Item[];
  numchild?: number;
  numchild_folder?: number;
  main_workspace?: boolean;
  path: string;
  url?: string;
  mimetype?: string;
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


export type TreeItemData = Omit<Item, "children"> & {
  parentId?: string;
}

export type TreeItem = TreeViewDataType<TreeItemData>


