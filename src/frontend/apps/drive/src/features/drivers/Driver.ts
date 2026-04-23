import {
  DTOCreateAccess,
  DTODeleteAccess,
  DTOUpdateAccess,
  DTOUpdateLinkConfiguration,
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
  ordering?: string;
  is_favorite?: boolean;
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

// Reason is a string that describes the reason for the entitlement result.
export type EntitlementReason = string;

export type Entitlement<T extends EntitlementReason> = {
  result: boolean;
  reason?: T;
  message?: string;
  [key: string]: unknown;
};

export enum EntitlementCanUploadReasons {
  NO_ORGANIZATION = "no_organization",
  NOT_ACTIVATED = "not_activated",
}

type EntitlementOperator = {
  id: string;
  name: string;
  siret: string;
  url: string | null;
  config: object;
  signupUrl: string;
};

type EntitlementOrganization = {
  id: string;
  type: string;
  name: string;
};

export type Entitlements = {
  can_access: Entitlement<never>;
  can_upload: Entitlement<EntitlementCanUploadReasons>;
  context: {
    organization?: EntitlementOrganization;
    operator?: EntitlementOperator;
    potentialOperators?: EntitlementOperator[];
  };
};

export abstract class Driver {
  abstract getConfig(): Promise<ApiConfig>;
  abstract getItems(filters?: ItemFilters): Promise<PaginatedChildrenResult>;
  abstract getTrashItems(filters?: ItemFilters): Promise<Item[]>;
  abstract getItem(id: string): Promise<Item>;
  abstract getItemBreadcrumb(id: string): Promise<ItemBreadcrumb[]>;
  abstract updateItem(item: Partial<Item>): Promise<Item>;
  abstract restoreItems(ids: string[]): Promise<void>;
  abstract moveItem(id: string, parentId?: string): Promise<void>;
  abstract moveItems(ids: string[], parentId?: string): Promise<void>;
  abstract getChildren(
    id: string,
    filters?: ItemFilters,
  ): Promise<PaginatedChildrenResult>;

  abstract searchItems(filters?: ItemFilters): Promise<Item[]>;
  // Accesses

  abstract getRecentItems(
    filters?: ItemFilters,
  ): Promise<PaginatedChildrenResult>;
  abstract getFavoriteItems(
    filters?: ItemFilters,
  ): Promise<PaginatedChildrenResult>;
  abstract createFavoriteItem(itemId: string): Promise<void>;
  abstract deleteFavoriteItem(itemId: string): Promise<void>;
  abstract getItemAccesses(itemId: string): Promise<Access[]>;
  abstract createAccess(data: DTOCreateAccess): Promise<void>;
  abstract updateAccess(payload: DTOUpdateAccess): Promise<Access | void>;
  abstract updateLinkConfiguration(
    payload: DTOUpdateLinkConfiguration,
  ): Promise<void>;
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
    parentId?: string;
    filename: string;
    file: File;
    progressHandler?: (progress: number) => void;
  }): { promise: Promise<Item>; abort: () => Promise<void> };
  abstract createFileFromTemplate(data: {
    parentId: string;
    extension: string;
    title: string;
  }): Promise<Item>;
  abstract duplicateItem(id: string): Promise<Item>;
  abstract deleteItems(ids: string[]): Promise<void>;
  abstract hardDeleteItems(ids: string[]): Promise<void>;
  abstract getWopiInfo(itemId: string): Promise<WopiInfo>;

  abstract getEntitlements(): Promise<Entitlements>;
}
