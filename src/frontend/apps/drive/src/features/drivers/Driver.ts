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

/**
 * Thrown by `moveItem` when the move can't be completed in-place
 * because it crosses an encryption boundary that needs the
 * recursive-encryption flow:
 *   - moving a plaintext item INTO an encrypted folder (must encrypt
 *     each item under the new parent's chain), or
 *   - moving an encrypted item OUT of its encryption root (or into a
 *     different encryption root) — currently unsupported, would need
 *     decrypt-then-re-encrypt for the destination.
 *
 * The React-side `useMoveItems` hook catches this and routes through
 * `ModalRecursiveEncrypt` to handle the encryption work, then retries
 * the move once the items are in the right state.
 */
export class MoveRequiresEncryption extends Error {
  constructor(
    public readonly itemId: string,
    public readonly reason:
      | 'plaintext-into-encrypted'
      | 'encrypted-out-of-root'
      | 'encrypted-cross-root',
  ) {
    super(`Move ${itemId} requires encryption flow: ${reason}`);
    this.name = 'MoveRequiresEncryption';
  }
}

export enum ItemFiltersScope {
  ALL = "all",
  DELETED = "deleted",
  NOT_DELETED = "not_deleted",
}

export enum ItemFiltersOrdering {
  CREATED_AT_ASC = "created_at",
  CREATED_AT_DESC = "-created_at",
  UPDATED_AT_ASC = "updated_at",
  UPDATED_AT_DESC = "-updated_at",
  TITLE_ASC = "title",
  TITLE_DESC = "-title",
  TYPE_ASC = "type",
  TYPE_DESC = "-type",
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
  /**
   * Move a single item under a new parent (or to root when `parentId` is
   * omitted).
   *
   * Encryption-aware: when the moved item is encrypted, its `K_item` is
   * wrapped under its OLD parent's key. The driver decides what to do
   * about that based on the source/destination encryption state:
   *   - source encrypted + destination encrypted (same encryption root):
   *     re-wrap K_item under the new parent's key (via the vault
   *     `rewrapNestedKey` op) before persisting the move; the file's
   *     content is left untouched.
   *   - source plaintext + destination encrypted: throws
   *     `MoveRequiresEncryption` so the caller can route through the
   *     recursive-encryption flow.
   *   - source encrypted, destination plaintext OR different encryption
   *     root: throws `MoveRequiresEncryption` (we'd need a re-encrypt
   *     pipeline that's out of scope here).
   *   - everything else: plain move.
   */
  abstract moveItem(id: string, parentId?: string): Promise<void>;
  abstract moveItems(ids: string[], parentId?: string): Promise<void>;
  abstract getChildren(
    id: string,
    filters?: ItemFilters
  ): Promise<PaginatedChildrenResult>;

  abstract searchItems(filters?: ItemFilters): Promise<Item[]>;
  // Accesses

  abstract getRecentItems(
    filters?: ItemFilters
  ): Promise<PaginatedChildrenResult>;
  abstract getFavoriteItems(
    filters?: ItemFilters
  ): Promise<PaginatedChildrenResult>;
  abstract createFavoriteItem(itemId: string): Promise<void>;
  abstract deleteFavoriteItem(itemId: string): Promise<void>;
  abstract getItemAccesses(itemId: string): Promise<Access[]>;
  abstract createAccess(data: DTOCreateAccess): Promise<void>;
  abstract updateAccess(payload: DTOUpdateAccess): Promise<Access | void>;
  abstract updateLinkConfiguration(
    payload: DTOUpdateLinkConfiguration
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
  abstract getDescendants(id: string): Promise<Item[]>;
  abstract createFolder(data: {
    title: string;
    // Full parent Item. Omit for root / workspace-level creation.
    // When `parent.is_encrypted`, the driver mints a folder key
    // wrapped by the parent's chain.
    parent?: Item;
  }): Promise<Item>;
  abstract createWorkspace(data: {
    title: string;
    description: string;
  }): Promise<Item>;
  abstract updateWorkspace(item: Partial<Item>): Promise<Item>;
  abstract deleteWorkspace(id: string): Promise<void>;
  abstract createFile(data: {
    // Full parent Item. Omit for root / workspace-level creation.
    // When `parent.is_encrypted`, the driver encrypts the content
    // client-side and sends the wrapped key.
    parent?: Item;
    filename: string;
  }): Promise<Item>;
  abstract createFileFromTemplate(data: {
    parentId?: string;
    extension: string;
    title: string;
  }): Promise<Item>;
  abstract deleteItems(ids: string[]): Promise<void>;
  abstract hardDeleteItems(ids: string[]): Promise<void>;
  abstract getWopiInfo(itemId: string): Promise<WopiInfo>;

  abstract getEntitlements(): Promise<Entitlements>;

  // Encryption
  abstract encryptItem(
    itemId: string,
    data: {
      encryptedSymmetricKeyPerUser: Record<string, string | null>;
      encryptionPublicKeyVersionPerUser: Record<string, number | null>;
      encryptedKeysForDescendants: Record<string, string>;
      fileKeyMapping?: Record<string, string>;
    }
  ): Promise<Item>;
  abstract removeEncryption(
    itemId: string,
    data?: { fileKeyMapping?: Record<string, string> }
  ): Promise<Item>;
  /**
   * Encrypt-on-move: ship a plaintext subtree into an encrypted destination
   * in one atomic backend call. The frontend has already encrypted file
   * contents under the destination's chain and uploaded to fresh S3 keys;
   * this commit writes the chain wraps + filename swap + path change in a
   * single transaction.
   *
   * Mirrors the /encrypt/ payload shape (encryptedKeysForDescendants +
   * fileKeyMapping) but produces a chain-rooted item — no per-user wraps,
   * no ItemAccess rows materialised, no inherited-collaborator bloat.
   */
  abstract moveItemEncryptOnMove(
    itemId: string,
    data: {
      targetItemId: string;
      encryptedSymmetricKey: string;
      encryptedKeysForDescendants: Record<string, string>;
      fileKeyMapping?: Record<string, string>;
    }
  ): Promise<void>;
  abstract getKeyChain(itemId: string): Promise<{
    user_access_item_id: string;
    encrypted_key_for_user: string;
    chain: Array<{ item_id: string; encrypted_symmetric_key: string }>;
  }>;
  abstract acceptEncryptionAccess(
    itemId: string,
    accessId: string,
    data: {
      encrypted_item_symmetric_key_for_user: string;
      encryption_public_key_version: number;
    }
  ): Promise<void>;
}
