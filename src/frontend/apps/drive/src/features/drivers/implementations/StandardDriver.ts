import { fetchAPI } from "@/features/api/fetchApi";
import { getRuntimeConfig } from "@/features/config/runtimeConfig";
import { AppError } from "@/features/errors/AppError";
import { UploadError } from "@/features/errors/UploadError";
import i18n from "@/features/i18n/initI18n";
import { getOperationTimeBound } from "@/features/operations/timeBounds";
import {
  Driver,
  Entitlements,
  ItemFilters,
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
    const bounds = getOperationTimeBound("config_load");
    const response = await fetchAPI(`config/`, undefined, {
      timeoutMs: bounds.fail_ms,
    });
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
    const response = await fetchAPI(`items/${id}/breadcrumb/`);
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

    const response = await fetchAPI(`items/${id}/children/`, {
      params,
    });
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
    const response = await fetchAPI(`items/${id}/tree/`);
    const data = await response.json();
    return jsonToItem(data);
  }

  async moveItem(id: string, parentId?: string): Promise<void> {
    const payload = {
      ...(parentId ? { target_item_id: parentId } : {}),
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
    await fetchAPI(`items/${data.itemId}/accesses/`, {
      method: "POST",
      body: JSON.stringify({
        user_id: data.userId,
        role: data.role,
      }),
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
    parentId?: string;
  }): Promise<Item> {
    const { parentId, ...rest } = data;
    const url = parentId ? `items/${parentId}/children/` : `items/`;
    const response = await fetchAPI(url, {
      method: "POST",
      body: JSON.stringify({
        ...rest,
        type: ItemType.FOLDER,
      }),
    });
    const item = await response.json();
    return jsonToItem(item);
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
    parentId?: string;
    file: File;
    filename: string;
    progressHandler?: (progress: number) => void;
  }): Promise<Item> {
    const config = getRuntimeConfig();
    const createBounds = getOperationTimeBound("upload_create", config);
    const uploadPutBounds = getOperationTimeBound("upload_put", config);
    const finalizeBounds = getOperationTimeBound("upload_finalize", config);

    const { parentId, file, progressHandler, ...rest } = data;
    const url = parentId ? `items/${parentId}/children/` : `items/`;
    const response = await fetchAPI(
      url,
      {
        method: "POST",
        body: JSON.stringify({
          type: ItemType.FILE,
          ...rest,
        }),
      },
      {
        // When entitlements are falsy, the backend returns a 403 error.
        // We don't want to redirect to the login page in this case, instead
        // we want to show an error.
        redirectOn40x: false,
        timeoutMs: createBounds.fail_ms,
      },
    );
    const item = jsonToItem(await response.json());
    if (!item.policy) {
      throw new AppError(i18n.t("api.error.unexpected"));
    }

    // We don't want to call the progress handler with 100% when the upload is done.
    // We want to wait until the upload-ended endpoint is called.
    const progressHandlerProxy = (progress: number) => {
      if (progress === 100) {
        return;
      }
      progressHandler?.(progress);
    };

    try {
      await uploadFile(
        item.policy,
        file,
        (progress) => progressHandlerProxy(progress),
        uploadPutBounds.fail_ms,
        { itemId: item.id },
      );
    } catch (error) {
      if (error instanceof UploadError) {
        throw error;
      }
      throw new UploadError({
        message: i18n.t("explorer.actions.upload.errors.put_failed"),
        kind: "put_failed",
        nextAction: "retry",
        itemId: item.id,
      });
    }

    try {
      await fetchAPI(
        `items/${item.id}/upload-ended/`,
        { method: "POST" },
        { redirectOn40x: false, timeoutMs: finalizeBounds.fail_ms },
      );
    } catch (error) {
      if (error instanceof UploadError) {
        throw error;
      }
      throw new UploadError({
        message: i18n.t("explorer.actions.upload.errors.finalize_failed"),
        kind: "finalize_failed",
        nextAction: "retry",
        itemId: item.id,
      });
    }

    progressHandler?.(100);

    return item;
  }

  async reinitiateFileUpload(data: {
    itemId: string;
    file: File;
    filename: string;
    progressHandler?: (progress: number) => void;
  }): Promise<void> {
    const config = getRuntimeConfig();
    const createBounds = getOperationTimeBound("upload_create", config);
    const uploadPutBounds = getOperationTimeBound("upload_put", config);
    const finalizeBounds = getOperationTimeBound("upload_finalize", config);

    const progressHandlerProxy = (progress: number) => {
      if (progress === 100) {
        return;
      }
      data.progressHandler?.(progress);
    };

    let policy: string;
    try {
      const response = await fetchAPI(
        `items/${data.itemId}/upload-policy/`,
        { method: "POST" },
        { redirectOn40x: false, timeoutMs: createBounds.fail_ms },
      );
      const payload = await response.json();
      policy = payload?.policy;
    } catch (_error) {
      throw new UploadError({
        message: i18n.t("explorer.actions.upload.errors.reinitiate_failed"),
        kind: "create_failed",
        nextAction: "contact_admin",
        itemId: data.itemId,
      });
    }

    if (!policy) {
      throw new UploadError({
        message: i18n.t("explorer.actions.upload.errors.reinitiate_failed"),
        kind: "create_failed",
        nextAction: "contact_admin",
        itemId: data.itemId,
      });
    }

    await uploadFile(
      policy,
      data.file,
      (progress) => progressHandlerProxy(progress),
      uploadPutBounds.fail_ms,
      { itemId: data.itemId },
    );

    await fetchAPI(
      `items/${data.itemId}/upload-ended/`,
      { method: "POST" },
      { redirectOn40x: false, timeoutMs: finalizeBounds.fail_ms },
    );

    data.progressHandler?.(100);
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
    const config = getRuntimeConfig();
    const bounds = getOperationTimeBound("wopi_info", config);
    const response = await fetchAPI(`items/${itemId}/wopi/`, undefined, {
      timeoutMs: bounds.fail_ms,
    });
    const data = await response.json();
    return data;
  }

  async getEntitlements(): Promise<Entitlements> {
    const response = await fetchAPI(`entitlements/`);
    const data = await response.json();
    return data;
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
  timeoutMs?: number,
  opts?: { itemId?: string },
) =>
  new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("PUT", url);
    xhr.setRequestHeader("X-amz-acl", "private");
    xhr.setRequestHeader("Content-Type", file.type);

    if (timeoutMs !== undefined) {
      xhr.timeout = timeoutMs;
    }

    const rejectWith = (params: {
      message: string;
      kind: "put_failed" | "timeout";
      nextAction: "retry" | "reinitiate" | "contact_admin";
    }) => {
      reject(
        new UploadError({
          message: params.message,
          kind: params.kind,
          nextAction: params.nextAction,
          itemId: opts?.itemId,
        }),
      );
    };

    xhr.addEventListener("error", () =>
      rejectWith({
        message: i18n.t("explorer.actions.upload.errors.put_failed"),
        kind: "put_failed",
        nextAction: "retry",
      }),
    );
    xhr.addEventListener("abort", () =>
      rejectWith({
        message: i18n.t("explorer.actions.upload.errors.put_failed"),
        kind: "put_failed",
        nextAction: "retry",
      }),
    );
    xhr.addEventListener("timeout", () => {
      rejectWith({
        message: i18n.t("explorer.actions.upload.errors.timeout"),
        kind: "timeout",
        nextAction: "retry",
      });
    });

    xhr.addEventListener("readystatechange", () => {
      if (xhr.readyState === 4) {
        if (xhr.status === 200) {
          // Make sure to always set the progress to 100% when the upload is done.
          // Because 'progress' event listener is not called when the file size is 0.
          progressHandler(100);
          return resolve(true);
        }
        const status = xhr.status;
        if (status === 400 || status === 403) {
          return rejectWith({
            message: i18n.t("explorer.actions.upload.errors.policy_expired"),
            kind: "put_failed",
            nextAction: "reinitiate",
          });
        }
        if (status >= 500) {
          return rejectWith({
            message: i18n.t("explorer.actions.upload.errors.storage_unavailable"),
            kind: "put_failed",
            nextAction: "retry",
          });
        }
        return rejectWith({
          message: i18n.t("explorer.actions.upload.errors.put_failed"),
          kind: "put_failed",
          nextAction: "retry",
        });
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
