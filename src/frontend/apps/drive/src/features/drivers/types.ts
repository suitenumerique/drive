import { TreeViewDataType } from "@gouvfr-lasuite/ui-kit";

export enum ItemType {
  FILE = "file",
  FOLDER = "folder",
}

export type Item = {
  id: string;
  title: string;
  filename: string;
  creator: {
    full_name: string;
    short_name: string;
  };
  type: ItemType;
  upload_state: string;
  updated_at: Date;
  description: string;
  created_at: Date;
  children?: Item[];
  numchild?: number;
  nb_accesses?: number;
  numchild_folder?: number;
  main_workspace?: boolean;
  path: string;
  url?: string;
  size?: number;
  mimetype?: string;
  user_roles?: Role[];
  abilities?: {
    accesses_manage: boolean;
    accesses_view: boolean;
    children_create: boolean;
    children_list: boolean;
    destroy: boolean;
    favorite: boolean;
    invite_owner: boolean;
    link_configuration: boolean;
    media_auth: boolean;  
    move: boolean;
    partial_update: boolean;
    restore: boolean;
    retrieve: boolean;
    tree: boolean;
    update: boolean;
    upload_ended: boolean;
  };
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


export type Access = {
  id: string;
  role: string;
  team: string;
  user: User;
  abilities: {
    destroy: boolean;
    partial_update: boolean;
    retrieve: boolean;
    set_role_to: Role[];
    update: boolean;
  };
}

export type Invitation = {
  team: string;
  user: User;
  id: string;
  role: Role;
  document: string;
  created_at: string;
  is_expired: boolean;
  issuer: string;
  email: string;
  abilities: {
    destroy: boolean;
    retrieve: boolean;
    partial_update: boolean;
    update: boolean;
  };
}

export enum Role {
  READER = 'reader',
  EDITOR = 'editor',
  ADMIN = 'administrator',
  OWNER = 'owner',
}

export type User = {
  id: string;
  email: string;
  full_name: string;
  short_name: string;
  language: string;
}


export interface APIList<T> {
  count: number;
  next?: string | null;
  previous?: string | null;
  results: T[];
}
