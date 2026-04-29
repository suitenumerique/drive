import { fetchAPI } from "@/features/api/fetchApi";
import { fromBase64, toBase64 } from "@/features/encryption/recursive/binary";
import {
  Driver,
  Entitlements,
  ItemFilters,
  MoveRequiresEncryption,
  UserFilters,
  PaginatedChildrenResult,
} from "../Driver";
import {
  DTODeleteInvitation,
  DTOCreateInvitation,
  DTOUpdateInvitation,
} from "../DTOs/InvitationDTO";
import {
  DTOCreateAccess,
  DTOUpdateLinkConfiguration,
} from "../DTOs/AccessesDTO";
import { DTOUpdateAccess } from "../DTOs/AccessesDTO";
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
} from "../types";
import { DTODeleteAccess } from "../DTOs/AccessesDTO";

export class StandardDriver extends Driver {
  async getConfig(): Promise<ApiConfig> {
    const response = await fetchAPI(`config/`);
    const data = await response.json();
    return data;
  }

  async getItems(filters: ItemFilters = {}): Promise<PaginatedChildrenResult> {
    const params = {
      page: 1,
      page_size: 100,
      ordering: "-type,-created_at",
      ...(filters ? filters : {}),
    };
    const response = await fetchAPI(`items/`, {
      params,
    });
    const data = await response.json();
    return {
      children: jsonToItems(data.results),
      pagination: {
        currentPage: filters.page ?? 1,
        totalCount: data.count,
        hasMore: data.next !== null,
      },
    };
  }

  async getItemBreadcrumb(id: string): Promise<ItemBreadcrumb[]> {
    const response = await fetchAPI(`items/${id}/breadcrumb/`, undefined, {
      redirectOn40x: false,
    });
    const data = await response.json();
    return data;
  }

  async searchItems(filters?: ItemFilters): Promise<Item[]> {
    const response = await fetchAPI(`items/search/`, {
      params: filters,
    });
    const data = await response.json();
    return jsonToItems(data.results);
  }

  async getTrashItems(filters?: ItemFilters): Promise<Item[]> {
    const response = await fetchAPI(`items/trashbin/`, {
      params: { ...filters, page_size: 200 },
    });
    const data = await response.json();
    return jsonToItems(data.results);
  }

  async getItem(id: string): Promise<Item> {
    const response = await fetchAPI(`items/${id}/`);
    const data = await response.json();
    return jsonToItem(data);
  }

  async updateItem(item: Partial<Item>): Promise<Item> {
    const response = await fetchAPI(`items/${item.id}/`, {
      method: "PATCH",
      body: JSON.stringify(item),
    });
    const data = await response.json();
    return jsonToItem(data);
  }

  async restoreItems(ids: string[]): Promise<void> {
    for (const id of ids) {
      await fetchAPI(`items/${id}/restore/`, {
        method: "POST",
      });
    }
  }

  async getUsers(filters?: UserFilters): Promise<User[]> {
    const response = await fetchAPI(`users/`, {
      params: filters,
    });
    const data = await response.json();
    return data;
  }

  async updateUser(payload: Partial<User> & { id: string }): Promise<User> {
    const response = await fetchAPI(`users/${payload.id}/`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    return data;
  }

  async getChildren(
    id: string,
    filters?: ItemFilters,
  ): Promise<PaginatedChildrenResult> {
    const params = {
      page: 1,
      page_size: filters?.page_size || 200,
      ordering: "-type,-created_at",
      ...(filters ? filters : {}),
    };

    const response = await fetchAPI(
      `items/${id}/children/`,
      { params },
      { redirectOn40x: false },
    );
    const data = await response.json();

    return {
      children: jsonToItems(data.results),
      pagination: {
        currentPage: params.page,
        totalCount: data.count,
        hasMore: data.next !== null,
      },
    };
  }

  async getTree(id: string): Promise<Item> {
    const response = await fetchAPI(`items/${id}/tree/`, undefined, {
      redirectOn40x: false,
    });
    const data = await response.json();
    return jsonToItem(data);
  }

  async getDescendants(id: string): Promise<Item[]> {
    const response = await fetchAPI(`items/${id}/descendants/`, undefined, {
      redirectOn40x: false,
    });
    const data = await response.json();
    return jsonToItems(data);
  }

  async moveItem(id: string, parentId?: string): Promise<void> {
    // Encryption-aware move. Four resolved cases:
    //
    //   1. Plain → plain: vanilla POST.
    //   2. Encrypted → encrypted, SAME root: rewrap K_item under the
    //      destination parent's chain (`vaultClient.rewrapNestedKey`)
    //      and ship the new wrap with the move. Item stays in the
    //      tree, content untouched.
    //   3. Encrypted → plaintext OR workspace root: re-anchor the
    //      item as its OWN encryption root. K_item recovered from
    //      the user's chain, then re-wrapped per-user via
    //      `shareKeys`; new wraps go into each access row's
    //      `encrypted_item_symmetric_key_for_user`. Backend flips
    //      `is_encryption_root: true` on the item and clears its
    //      chain wrap.
    //   4. Self-rooted encrypted → encrypted subtree (item is its
    //      own encryption root, destination is in a different tree):
    //      attach the item under the destination's chain by wrapping
    //      K_item under the destination parent's terminal key
    //      (`vaultClient.wrapNestedKey`). Backend flips
    //      `is_encryption_root: false`, writes `encrypted_symmetric_key`,
    //      and clears the per-user wraps on access rows.
    //
    //   Throws `MoveRequiresEncryption('plaintext-into-encrypted')`
    //   when the source is plaintext and the destination is in an
    //   encrypted subtree — the React layer routes that through the
    //   recursive-encryption modal first, then retries the move.
    //
    //   Throws `MoveRequiresEncryption('encrypted-cross-root')` for
    //   tree-A → tree-B chain-rooted moves (would need decrypt +
    //   re-wrap-as-self-root + re-attach). Not handled yet.
    const item = await this.getItem(id);
    const targetParent = parentId ? await this.getItem(parentId) : null;

    const sourceEncrypted = !!item.is_encrypted;
    const sourceIsRoot = !!item.is_encryption_root;
    const targetEncrypted = !!targetParent?.is_encrypted;

    let encryptedSymmetricKey: string | undefined;
    // Map of user sub → base64 K_item wrapped under their pubkey, or
    // `null` when the user has access but hasn't published an
    // encryption pubkey yet. Backend uses `null` as a sentinel to
    // mark the access row pending; the wrap can be filled in later
    // via the share UI once the user has onboarded.
    let perUserEncryptedKeys: Record<string, string | null> | undefined;
    // Matched pair with `perUserEncryptedKeys`: same key set, value is
    // the fingerprint of the user's pubkey at wrap time (or null when
    // the user is pending). Backend stores it on the access row so
    // clients can later detect a key-rotation mismatch.
    let perUserFingerprints: Record<string, string | null> | undefined;
    let isEncryptionRoot: boolean | undefined; // present iff the move toggles the flag

    if (sourceEncrypted && targetEncrypted && sourceIsRoot) {
      // Case 4: self-rooted source attaches under destination chain.
      const vaultClient = window.__driveVaultClient;
      if (!vaultClient) {
        throw new Error('Vault client not initialized — cannot wrap key for move.');
      }
      // The item's per-user wrap on the caller's access row.
      const userEncryptedKey = item.encrypted_item_symmetric_key_for_user;
      if (!userEncryptedKey) {
        throw new Error(
          'Self-rooted encrypted item has no per-user wrap on the caller — cannot derive K_item.',
        );
      }
      const newParentKeyChain = await this.getKeyChain(parentId!);
      const newEntryKey = fromBase64(newParentKeyChain.encrypted_key_for_user);
      const newChainToParent = newParentKeyChain.chain.map(e =>
        fromBase64(e.encrypted_symmetric_key),
      );

      const { newEncryptedKey } = await vaultClient.wrapNestedKey(
        fromBase64(userEncryptedKey),
        newEntryKey,
        newChainToParent.length > 0 ? newChainToParent : undefined,
      );
      encryptedSymmetricKey = toBase64(newEncryptedKey);
      isEncryptionRoot = false; // demoting from self-root into the chain
    } else if (sourceEncrypted && targetEncrypted) {
      // Case 2: same-root rewrap.
      const oldKeyChain = await this.getKeyChain(id);
      const newParentKeyChain = await this.getKeyChain(parentId!);

      // Cross-root detection: compare the encryption tree root each
      // item belongs to. If they're the same, source and target are
      // in the same encrypted subtree — a chain rewrap is enough.
      // If they differ, this is the "tree A → tree B" case — would
      // need decrypt + re-wrap-as-self-root then re-attach (Case 4
      // composed with Case 3); not yet handled in one shot.
      //
      // `user_access_item_id` would be wrong here: hybrid items (a
      // self-rooted file demoted into a chain) keep their per-user
      // wrap, so the deepest-first walker resolves entry to the
      // item itself, not its tree root — making same-tree moves
      // look cross-root.
      if (
        oldKeyChain.encryption_tree_root_item_id !==
        newParentKeyChain.encryption_tree_root_item_id
      ) {
        throw new MoveRequiresEncryption(id, 'encrypted-cross-root');
      }

      const vaultClient = window.__driveVaultClient;
      if (!vaultClient) {
        throw new Error('Vault client not initialized — cannot rewrap key for move.');
      }

      const entryKey = fromBase64(oldKeyChain.encrypted_key_for_user);
      // `getKeyChain(itemId).chain` resolves to ITEM's own key — its
      // last element is K_item wrapped under the OLD parent. Strip
      // that to get the chain to the OLD parent itself.
      const oldChainToParent = oldKeyChain.chain
        .slice(0, -1)
        .map(e => fromBase64(e.encrypted_symmetric_key));
      const oldEncryptedKey = fromBase64(
        oldKeyChain.chain[oldKeyChain.chain.length - 1].encrypted_symmetric_key,
      );
      const newChainToParent = newParentKeyChain.chain.map(e =>
        fromBase64(e.encrypted_symmetric_key),
      );

      const { newEncryptedKey } = await vaultClient.rewrapNestedKey(
        entryKey,
        oldEncryptedKey,
        oldChainToParent.length > 0 ? oldChainToParent : undefined,
        newChainToParent.length > 0 ? newChainToParent : undefined,
      );
      encryptedSymmetricKey = toBase64(newEncryptedKey);
    } else if (!sourceEncrypted && targetEncrypted) {
      throw new MoveRequiresEncryption(id, 'plaintext-into-encrypted');
    } else if (sourceEncrypted && !targetEncrypted) {
      // Case 3: re-anchor as its own encryption root.
      const vaultClient = window.__driveVaultClient;
      if (!vaultClient) {
        throw new Error('Vault client not initialized — cannot re-anchor for move.');
      }

      const oldKeyChain = await this.getKeyChain(id);
      const entryKey = fromBase64(oldKeyChain.encrypted_key_for_user);
      // `oldKeyChain.chain` resolves to the item's own K_item — pass
      // it as-is so `shareKeys` lands on K_item, then re-wraps it
      // for each user's pubkey.
      const chainToItem = oldKeyChain.chain.map(e =>
        fromBase64(e.encrypted_symmetric_key),
      );

      // Collect every user with current access. The encryption server
      // keys on the OIDC `sub` (cross-product identifier —
      // `suiteUserId` inside the vault), NOT Drive's local user UUID.
      // `Access.user.sub` is the right field; `Access.user.id` would
      // silently miss everyone.
      const accesses = await this.getItemAccesses(id);
      const userSubs = Array.from(
        new Set(accesses.map(a => a.user.sub).filter(Boolean)),
      );
      if (userSubs.length === 0) {
        throw new Error(
          'No users with access — cannot re-anchor item as its own encryption root.',
        );
      }
      const { publicKeys } = await vaultClient.fetchPublicKeys(userSubs);
      const usersWithKeys = new Set(Object.keys(publicKeys));

      // The only catastrophic case is the OPERATOR (the user doing
      // the move) lacking a published pubkey — re-anchoring without
      // their wrap would lock them out of their own file. Refuse the
      // move in that single case; surface a clear error.
      //
      // Other collaborators without keys aren't refused — we mark
      // their access rows as pending (`null` wrap) and the share UI
      // can later top them up once they finish onboarding. This
      // mirrors how new shares work for not-yet-onboarded users.
      const actorSub = vaultClient.getAuthContext?.()?.suiteUserId;
      if (!actorSub) {
        throw new Error(
          'Vault auth context is not set — cannot determine the operator for the re-anchor guard.',
        );
      }
      if (!usersWithKeys.has(actorSub)) {
        throw new Error(
          "Your encryption keys aren't published yet — moving this item out of its encryption root would lock you out. Complete encryption setup first.",
        );
      }

      // Wrap K_item only for users who have a pubkey; the rest get a
      // `null` placeholder that the backend will treat as pending.
      const { encryptedKeys } = await vaultClient.shareKeys(
        entryKey,
        publicKeys,
        chainToItem.length > 0 ? chainToItem : undefined,
      );
      perUserEncryptedKeys = {};
      // Fingerprints travel as matched pairs with the per-user wraps —
      // the backend writes `(encrypted_item_symmetric_key_for_user,
      // encryption_public_key_fingerprint)` together on each access
      // row, identical to /encrypt/.
      perUserFingerprints = {};
      for (const userSub of userSubs) {
        const wrap = encryptedKeys[userSub];
        perUserEncryptedKeys[userSub] = wrap ? toBase64(wrap) : null;
        const pubKey = publicKeys[userSub];
        perUserFingerprints[userSub] = pubKey
          ? await vaultClient.computeKeyFingerprint(pubKey)
          : null;
      }
      const pendingCount = userSubs.length - usersWithKeys.size;
      if (pendingCount > 0) {
        console.info(
          '[StandardDriver.moveItem] re-anchor: marking',
          pendingCount,
          'collaborator access row(s) as pending — they will be re-shared once their pubkey is available.',
        );
      }
      isEncryptionRoot = true; // promoting to self-root on the way out
    }

    const payload: Record<string, unknown> = {
      ...(parentId ? { target_item_id: parentId } : {}),
      ...(encryptedSymmetricKey
        ? { encrypted_symmetric_key: encryptedSymmetricKey }
        : {}),
      ...(typeof isEncryptionRoot === 'boolean'
        ? { is_encryption_root: isEncryptionRoot }
        : {}),
      ...(perUserEncryptedKeys
        ? { per_user_encrypted_keys: perUserEncryptedKeys }
        : {}),
      ...(perUserFingerprints
        ? { encryption_public_key_fingerprints: perUserFingerprints }
        : {}),
    };
    await fetchAPI(`items/${id}/move/`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  }

  async getItemAccesses(itemId: string): Promise<Access[]> {
    const response = await fetchAPI(`items/${itemId}/accesses/`);
    const data = await response.json();
    return data;
  }

  async createAccess(data: DTOCreateAccess): Promise<void> {
    const body: Record<string, unknown> = {
      user_id: data.userId,
      role: data.role,
    };
    if (data.encrypted_item_symmetric_key_for_user) {
      body.encrypted_item_symmetric_key_for_user =
        data.encrypted_item_symmetric_key_for_user;
    }
    if (data.encryption_public_key_fingerprint) {
      body.encryption_public_key_fingerprint =
        data.encryption_public_key_fingerprint;
    }
    await fetchAPI(`items/${data.itemId}/accesses/`, {
      method: "POST",
      body: JSON.stringify(body),
    });
  }

  async deleteAccess(payload: DTODeleteAccess): Promise<void> {
    await fetchAPI(`items/${payload.itemId}/accesses/${payload.accessId}/`, {
      method: "DELETE",
    });
  }

  async updateLinkConfiguration(
    payload: DTOUpdateLinkConfiguration,
  ): Promise<void> {
    const { itemId, ...rest } = payload;
    await fetchAPI(`items/${itemId}/link-configuration/`, {
      method: "PUT",
      body: JSON.stringify(rest),
    });
  }

  async updateAccess({
    itemId,
    accessId,
    ...payload
  }: DTOUpdateAccess): Promise<Access | void> {
    const response = await fetchAPI(`items/${itemId}/accesses/${accessId}/`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });

    if (response.status === 204) {
      return;
    }

    const data = await response.json();
    return data;
  }

  async createInvitation(payload: DTOCreateInvitation): Promise<Invitation> {
    const response = await fetchAPI(`items/${payload.itemId}/invitations/`, {
      method: "POST",
      body: JSON.stringify({
        email: payload.email,
        role: payload.role,
      }),
    });
    const data = await response.json();
    return data;
  }

  async deleteInvitation(payload: DTODeleteInvitation): Promise<void> {
    await fetchAPI(
      `items/${payload.itemId}/invitations/${payload.invitationId}/`,
      {
        method: "DELETE",
      },
    );
  }

  async updateInvitation(payload: DTOUpdateInvitation): Promise<Invitation> {
    const response = await fetchAPI(
      `items/${payload.itemId}/invitations/${payload.invitationId}/`,
      {
        method: "PATCH",
        body: JSON.stringify(payload),
      },
    );
    const data = await response.json();
    return data;
  }

  async getItemInvitations(itemId: string): Promise<APIList<Invitation>> {
    const response = await fetchAPI(`items/${itemId}/invitations/`);
    const data = await response.json();
    return data;
  }

  async moveItems(ids: string[], parentId?: string): Promise<void> {
    for (const id of ids) {
      await this.moveItem(id, parentId);
    }
  }

  async createFolder(data: {
    title: string;
    parent?: Item;
  }): Promise<Item> {
    const { parent, ...rest } = data;
    const url = parent ? `items/${parent.id}/children/` : `items/`;
    const body: Record<string, unknown> = {
      ...rest,
      type: ItemType.FOLDER,
    };

    // If the parent is encrypted, the backend requires a wrapped
    // symmetric key for the new folder. Mint K_folder via the vault,
    // wrapped by the parent's key chain, and include it in the payload.
    if (parent?.is_encrypted) {
      body.encrypted_symmetric_key = await this.mintWrappedChildKey(parent);
    }

    const response = await fetchAPI(url, {
      method: "POST",
      body: JSON.stringify(body),
    });
    const item = await response.json();
    return jsonToItem(item);
  }

  // Mint a symmetric key for a new child of `parent` (folder or file),
  // wrapped by the parent's effective key. Returns the base64-encoded
  // wrapped key suitable for `encrypted_symmetric_key` on POST /children/.
  // The second return (for files) is the encrypted content; folders
  // encrypt an empty buffer they don't use.
  private async encryptForParent(
    parent: Item,
    content: ArrayBuffer,
  ): Promise<{ wrappedKey: string; encryptedContent: ArrayBuffer }> {
    const vaultClient = window.__driveVaultClient;
    if (!vaultClient) {
      throw new Error(
        "Vault client not initialized — cannot create an encrypted child.",
      );
    }
    const keyChain = await this.getKeyChain(parent.id);
    const entryKey = fromBase64(keyChain.encrypted_key_for_user);
    const chain = keyChain.chain.map((e) =>
      fromBase64(e.encrypted_symmetric_key),
    );
    const { encryptedContent, wrappedKey } = await vaultClient.encryptNestedWithoutKey(
      content,
      entryKey,
      chain,
    );
    return {
      wrappedKey: toBase64(wrappedKey),
      encryptedContent,
    };
  }

  private async mintWrappedChildKey(parent: Item): Promise<string> {
    const { wrappedKey } = await this.encryptForParent(
      parent,
      new ArrayBuffer(0),
    );
    return wrappedKey;
  }

  async createWorkspace(data: {
    title: string;
    description: string;
  }): Promise<Item> {
    const response = await fetchAPI(`items/`, {
      method: "POST",
      body: JSON.stringify({
        ...data,
        type: ItemType.FOLDER,
      }),
    });
    const item = await response.json();
    return jsonToItem(item);
  }

  async updateWorkspace(item: Partial<Item>): Promise<Item> {
    return this.updateItem(item);
  }

  async deleteWorkspace(id: string): Promise<void> {
    return this.deleteItems([id]);
  }

  async getRecentItems(
    filters?: ItemFilters,
  ): Promise<PaginatedChildrenResult> {
    const response = await fetchAPI(`items/recents/`, {
      params: { ...filters, page_size: 200 },
    });
    const data = await response.json();
    return {
      children: jsonToItems(data.results),
      pagination: {
        currentPage: filters?.page ?? 1,
        totalCount: data.count,
        hasMore: data.next !== null,
      },
    };
  }

  async getFavoriteItems(
    filters?: ItemFilters,
  ): Promise<PaginatedChildrenResult> {
    const response = await fetchAPI(`items/favorite_list/`, {
      params: { ...filters, page_size: 200 },
    });

    const data = await response.json();
    return {
      children: jsonToItems(data.results),
      pagination: {
        currentPage: filters?.page ?? 1,
        totalCount: data.count,
        hasMore: data.next !== null,
      },
    };
  }

  async createFavoriteItem(itemId: string): Promise<void> {
    await fetchAPI(`items/${itemId}/favorite/`, {
      method: "POST",
    });
  }

  async deleteFavoriteItem(itemId: string): Promise<void> {
    await fetchAPI(`items/${itemId}/favorite/`, {
      method: "DELETE",
    });
  }

  async createFile(data: {
    parent?: Item;
    file: File;
    filename: string;
    progressHandler?: (progress: number) => void;
  }): Promise<Item> {
    const { parent, file, progressHandler, ...rest } = data;
    const url = parent ? `items/${parent.id}/children/` : `items/`;

    const body: Record<string, unknown> = {
      type: ItemType.FILE,
      ...rest,
    };

    // If the parent is encrypted, mint K_file wrapped by the parent's
    // key and encrypt the file content client-side. The upload to the
    // policy URL then carries ciphertext; the backend /upload-ended/
    // short-circuits mimetype / malware analysis for encrypted items.
    let encryptedBody: ArrayBuffer | null = null;
    if (parent?.is_encrypted) {
      const plaintext = await file.arrayBuffer();
      const { wrappedKey, encryptedContent } = await this.encryptForParent(
        parent,
        plaintext,
      );
      body.encrypted_symmetric_key = wrappedKey;
      encryptedBody = encryptedContent;
    }

    const response = await fetchAPI(
      url,
      { method: "POST", body: JSON.stringify(body) },
      {
        // When entitlements are falsy, the backend returns a 403 error.
        // We don't want to redirect to the login page in this case, instead
        // we want to show an error.
        redirectOn40x: false,
      },
    );
    const item = jsonToItem(await response.json());
    if (!item.policy) {
      throw new Error("No policy found");
    }

    // We want the upload progress ( that goes from 0 to 100) to be proxied to the progress handler ( that goes from 0 to 95)
    // So the progression indicator still shows leave a 5% gap before the upload-ended is called.
    // We want to wait until the upload-ended endpoint is called.
    const progressHandlerProxy = (progress: number) => {
      const proxyScale = 90;
      const proxiedProgress = (progress * proxyScale) / 100;
      progressHandler?.(proxiedProgress);
    };

    if (encryptedBody) {
      // Upload ciphertext with progress. XHR lets us report progress which
      // fetch() can't do for request bodies.
      await uploadArrayBuffer(
        item.policy,
        encryptedBody,
        "application/octet-stream",
        (progress) => progressHandlerProxy(progress),
      );
    } else {
      await uploadFile(item.policy, file, (progress) => {
        progressHandlerProxy(progress);
      });
    }

    await fetchAPI(`items/${item.id}/upload-ended/`, {
      method: "POST",
    });

    progressHandler?.(100);

    return item;
  }

  async createFileFromTemplate(data: {
    parentId?: string;
    extension: string;
    title: string;
  }): Promise<Item> {
    const url = data.parentId ? `items/${data.parentId}/children/` : `items/`;

    const response = await fetchAPI(
      url,
      {
        method: "POST",
        body: JSON.stringify({
          type: "file",
          extension: data.extension,
          title: data.title,
        }),
      },
      {
        // When entitlements are falsy, the backend returns a 403 error.
        // We don't want to redirect to the login page in this case, instead
        // we want to show an error.
        redirectOn40x: false,
      },
    );
    return jsonToItem(await response.json());
  }

  async deleteItems(ids: string[]): Promise<void> {
    for (const id of ids) {
      await fetchAPI(`items/${id}/`, {
        method: "DELETE",
      });
    }
  }

  async hardDeleteItems(ids: string[]): Promise<void> {
    for (const id of ids) {
      await fetchAPI(`items/${id}/hard-delete/`, {
        method: "DELETE",
      });
    }
  }

  async getWopiInfo(itemId: string): Promise<WopiInfo> {
    const response = await fetchAPI(`items/${itemId}/wopi/`);
    const data = await response.json();
    return data;
  }

  async getEntitlements(): Promise<Entitlements> {
    const response = await fetchAPI(`entitlements/`);
    const data = await response.json();
    return data;
  }

  // Encryption

  async encryptItem(
    itemId: string,
    data: {
      encryptedSymmetricKeyPerUser: Record<string, string | null>;
      encryptionPublicKeyFingerprintPerUser: Record<string, string | null>;
      encryptedKeysForDescendants: Record<string, string>;
      fileKeyMapping?: Record<string, string>;
    },
  ): Promise<Item> {
    const response = await fetchAPI(`items/${itemId}/encrypt/`, {
      method: "PATCH",
      body: JSON.stringify(data),
    });
    const json = await response.json();
    return jsonToItem(json);
  }

  async removeEncryption(
    itemId: string,
    data?: { fileKeyMapping?: Record<string, string> },
  ): Promise<Item> {
    const response = await fetchAPI(`items/${itemId}/remove-encryption/`, {
      method: "PATCH",
      body: JSON.stringify(data ?? {}),
    });
    const json = await response.json();
    return jsonToItem(json);
  }

  async getKeyChain(itemId: string): Promise<{
    user_access_item_id: string;
    encrypted_key_for_user: string;
    /**
     * Identity of the encryption tree the item belongs to — the deepest
     * encryption root that's an ancestor (or self) of `itemId`. Stable
     * across hybrid wraps (demoted self-rooted items still expose the
     * outer tree root here, even though their own access row carries a
     * per-user wrap). Use THIS field for cross-root comparisons on
     * moves; `user_access_item_id` is the user's entry point and can
     * land on the item itself for hybrids.
     */
    encryption_tree_root_item_id: string | null;
    chain: Array<{ item_id: string; encrypted_symmetric_key: string }>;
  }> {
    const response = await fetchAPI(`items/${itemId}/key-chain/`);
    return response.json();
  }

  async acceptEncryptionAccess(
    itemId: string,
    accessId: string,
    data: {
      encrypted_item_symmetric_key_for_user: string;
      encryption_public_key_fingerprint: string;
    },
  ): Promise<void> {
    await fetchAPI(
      `items/${itemId}/accesses/${accessId}/encryption-key/`,
      {
        method: "PATCH",
        body: JSON.stringify(data),
      },
    );
  }
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const jsonToItems = (data: any[]): Item[] => {
  return data.map((v) => jsonToItem(v));
};

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const jsonToItem = (data: any): Item => {
  const item = {
    ...data,
    updated_at: new Date(data.updated_at),
  };
  if (data.children) {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    item.children = data.children.map((v: any) => jsonToItem(v));
  }
  return item;
};

/**
 * Upload a file, using XHR so we can report on progress through a handler.
 * @param url The URL to POST the file to.
 * @param formData The multi-part request form data body to send (includes the file).
 * @param progressHandler A handler that receives progress updates as a single integer `0 <= x <= 100`.
 */
export const uploadFile = (
  url: string,
  file: File,
  progressHandler: (progress: number) => void,
) =>
  new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("PUT", url);
    xhr.setRequestHeader("X-amz-acl", "private");
    xhr.setRequestHeader("Content-Type", file.type);

    xhr.addEventListener("error", reject);
    xhr.addEventListener("abort", reject);

    xhr.addEventListener("readystatechange", () => {
      if (xhr.readyState === 4) {
        if (xhr.status === 200) {
          // Make sure to always set the progress to 100% when the upload is done.
          // Because 'progress' event listener is not called when the file size is 0.
          progressHandler(100);
          return resolve(true);
        }
        reject(new Error(`Failed to perform the upload on ${url}.`));
      }
    });

    xhr.upload.addEventListener("progress", (progressEvent) => {
      if (progressEvent.lengthComputable) {
        progressHandler(
          Math.floor((progressEvent.loaded / progressEvent.total) * 100),
        );
      }
    });

    xhr.send(file);
  });

/**
 * Upload raw bytes to a presigned PUT URL with progress reporting. Used
 * for encrypted content where the ciphertext is held as an ArrayBuffer
 * rather than a File object.
 */
export const uploadArrayBuffer = (
  url: string,
  buffer: ArrayBuffer,
  contentType: string,
  progressHandler: (progress: number) => void,
) =>
  new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("PUT", url);
    xhr.setRequestHeader("X-amz-acl", "private");
    xhr.setRequestHeader("Content-Type", contentType);

    xhr.addEventListener("error", reject);
    xhr.addEventListener("abort", reject);

    xhr.addEventListener("readystatechange", () => {
      if (xhr.readyState === 4) {
        if (xhr.status === 200) {
          progressHandler(100);
          return resolve(true);
        }
        reject(new Error(`Failed to perform the upload on ${url}.`));
      }
    });

    xhr.upload.addEventListener("progress", (progressEvent) => {
      if (progressEvent.lengthComputable) {
        progressHandler(
          Math.floor((progressEvent.loaded / progressEvent.total) * 100),
        );
      }
    });

    xhr.send(buffer);
  });
