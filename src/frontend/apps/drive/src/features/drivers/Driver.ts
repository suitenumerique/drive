import {
  DTOCreateAccess,
  DTODeleteAccess,
  DTOUpdateAccess,
} from "./DTOs/AccessesDTO";
import {
  DTOCreateInvitation,
  DTODeleteInvitation,
  DTOUpdateInvitation,
} from "./DTOs/InvitationDTO";
import {
  Access,
  ApiConfig,
  APIList,
  Invitation,
  Item,
  ItemBreadcrumb,
  ItemType,
  User,
  WopiInfo,
  WorkspaceType,
} from "./types";

export enum ItemFiltersScope {
  ALL = "all",
  DELETED = "deleted",
  NOT_DELETED = "not_deleted",
}

export type ItemFilters = {
  type?: ItemType;
  title?: string;
  workspace?: string;
  scope?: ItemFiltersScope;
  page?: number;
  page_size?: number;
  workspaces?: WorkspaceType;
  is_creator_me?: boolean;
};

export type PaginatedChildrenResult = {
  children: Item[];
  pagination: {
    currentPage: number;
    totalCount?: number;
    hasMore: boolean;
  };
};
export type UserFilters = {
  q?: string;
};

export type Entitlement = {
  result: boolean;
  message?: string;
  [key: string]: unknown;
};

export type Entitlements = {
  can_access: Entitlement;
  can_upload: Entitlement;
};

export abstract class Driver {
  abstract getConfig(): Promise<ApiConfig>;
  abstract getItems(filters?: ItemFilters): Promise<PaginatedChildrenResult>;
  abstract getTrashItems(filters?: ItemFilters): Promise<Item[]>;
  abstract getItem(id: string): Promise<Item>;
  abstract getItemBreadcrumb(id: string): Promise<ItemBreadcrumb[]>;
  abstract updateItem(item: Partial<Item>): Promise<Item>;
  abstract restoreItems(ids: string[]): Promise<void>;
  abstract moveItem(id: string, parentId: string): Promise<void>;
  abstract moveItems(ids: string[], parentId: string): Promise<void>;
  abstract getChildren(
    id: string,
    filters?: ItemFilters
  ): Promise<PaginatedChildrenResult>;

  abstract searchItems(filters?: ItemFilters): Promise<Item[]>;
  // Accesses
  abstract getItemAccesses(itemId: string): Promise<APIList<Access>>;
  abstract createAccess(data: DTOCreateAccess): Promise<void>;
  abstract updateAccess(payload: DTOUpdateAccess): Promise<Access>;
  abstract deleteAccess(payload: DTODeleteAccess): Promise<void>;
  // Invitations
  abstract getItemInvitations(itemId: string): Promise<APIList<Invitation>>;
  abstract createInvitation(data: DTOCreateInvitation): Promise<Invitation>;
  abstract deleteInvitation(payload: DTODeleteInvitation): Promise<void>;
  abstract updateInvitation(payload: DTOUpdateInvitation): Promise<Invitation>;

  // Users
  abstract getUsers(filters?: UserFilters): Promise<User[]>;
  abstract updateUser(payload: Partial<User> & { id: string }): Promise<User>;
  // Tree
  abstract getTree(id: string): Promise<Item>;
  abstract createFolder(data: { title: string }): Promise<Item>;
  abstract createWorkspace(data: {
    title: string;
    description: string;
  }): Promise<Item>;
  abstract updateWorkspace(item: Partial<Item>): Promise<Item>;
  abstract deleteWorkspace(id: string): Promise<void>;
  abstract createFile(data: {
    parentId: string;
    filename: string;
  }): Promise<Item>;
  abstract deleteItems(ids: string[]): Promise<void>;
  abstract hardDeleteItems(ids: string[]): Promise<void>;
  abstract getWopiInfo(itemId: string): Promise<WopiInfo>;

  abstract getEntitlements(): Promise<Entitlements>;
}
