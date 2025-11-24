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

export type ItemBreadcrumb = {
  id: string;
  title: string;
  path: string;
  depth: number;
  main_workspace: boolean;
};

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
  deleted_at?: Date;
  upload_state: string;
  updated_at: Date;
  description: string;
  is_wopi_supported?: boolean;
  created_at: Date;
  children?: Item[];
  parents?: Item[];
  breadcrumb?: ItemBreadcrumb[];
  numchild?: number;
  nb_accesses?: number;
  numchild_folder?: number;
  main_workspace?: boolean;
  path: string;
  url?: string;
  url_preview?: string;
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
  policy?: string;
};

export type TreeItemData = Omit<Item, "children"> & {
  parentId?: string;
};

export type TreeItem = TreeViewDataType<TreeItemData>;

export type WopiInfo = {
  access_token: string;
  access_token_ttl: number;
  launch_url: string;
};

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

export type ElementConfigDisplay = {
  show: boolean;
}

export interface ThemeCustomization {
  footer?: LocalizedThemeCustomization<FooterProps>;
  auth_buttons?: ElementConfigDisplay;
  language_picker?: ElementConfigDisplay;
}

export type ApiConfig = {
  POSTHOG_KEY?: string;
  POSTHOG_HOST?: string;
  FRONTEND_MORE_LINK?: string;
  FRONTEND_FEEDBACK_BUTTON_SHOW?: boolean;
  FRONTEND_FEEDBACK_BUTTON_IDLE?: boolean;
  FRONTEND_FEEDBACK_ITEMS?: Record<string, { url: string }>;
  FRONTEND_FEEDBACK_MESSAGES_WIDGET_ENABLED?: boolean;
  FRONTEND_FEEDBACK_MESSAGES_WIDGET_API_URL?: string;
  FRONTEND_FEEDBACK_MESSAGES_WIDGET_CHANNEL?: string;
  FRONTEND_FEEDBACK_MESSAGES_WIDGET_PATH?: string;
  FRONTEND_THEME?: string;
  FRONTEND_HIDE_GAUFRE?: boolean;
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
