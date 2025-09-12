import { FooterProps, TreeViewDataType } from "@gouvfr-lasuite/ui-kit";

export enum ItemType {
  FILE = "file",
  FOLDER = "folder",
}

export enum LinkReach {
  RESTRICTED = "restricted",
  AUTHENTICATED = "authenticated",
  PUBLIC = "public",
}

export enum LinkRole {
  READER = "reader",
  EDITOR = "editor",
}

export enum ItemUploadState {
  PENDING = "pending",
  ANALYZING = "analyzing",
  SUSPICIOUS = "suspicious",
  FILE_TOO_LARGE_TO_ANALYZE = "file_too_large_to_analyze",
  READY = "ready",
}

export type Item = {
  id: string;
  title: string;
  filename: string;
  creator: {
    id: string;
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
  link_reach?: LinkReach;
  link_role?: LinkRole;
  abilities: {
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
};

export type TreeItem = TreeViewDataType<TreeItemData>;

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
};

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
};

export enum Role {
  READER = "reader",
  EDITOR = "editor",
  ADMIN = "administrator",
  OWNER = "owner",
}

export type User = {
  id: string;
  email: string;
  full_name: string;
  short_name: string;
  language: string;
};

export type LocalizedThemeCustomization<T> = {
  default: T;
  [key: string]: T;
};

export interface ThemeCustomization {
  footer?: LocalizedThemeCustomization<FooterProps>;
}

export type ApiConfig = {
  POSTHOG_KEY?: string;
  POSTHOG_HOST?: string;
  FRONTEND_MORE_LINK?: string;
  FRONTEND_FEEDBACK_BUTTON_SHOW?: boolean;
  FRONTEND_FEEDBACK_BUTTON_IDLE?: boolean;
  FRONTEND_FEEDBACK_ITEMS?: Record<string, { url: string }>;
  FRONTEND_THEME?: string;
  FRONTEND_HIDE_GAUFRE?: boolean;
  FRONTEND_SHOW_FOOTER?: boolean;
  theme_customization?: ThemeCustomization;
};

export interface APIList<T> {
  count: number;
  next?: string | null;
  previous?: string | null;
  results: T[];
}

export enum WorkspaceType {
  MAIN = "main",
  PUBLIC = "public",
  SHARED = "shared",
}
