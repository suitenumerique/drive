import { fetchAPI } from "@/features/api/fetchApi";
import {
  Driver,
  ItemFilters,
  PaginatedChildrenResult,
  UserFilters,
} from "../Driver";
import {
  DTODeleteInvitation,
  DTOCreateInvitation,
  DTOUpdateInvitation,
} from "../DTOs/InvitationDTO";
import { DTOCreateAccess } from "../DTOs/AccessesDTO";
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
    filters?: ItemFilters
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

  async moveItem(id: string, parentId: string): Promise<void> {
    await fetchAPI(`items/${id}/move/`, {
      method: "POST",
      body: JSON.stringify({ target_item_id: parentId }),
    });
  }

  async getItemAccesses(itemId: string): Promise<APIList<Access>> {
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

  async updateAccess({
    itemId,
    accessId,
    ...payload
  }: DTOUpdateAccess): Promise<Access> {
    const response = await fetchAPI(`items/${itemId}/accesses/${accessId}/`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
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
      }
    );
  }

  async updateInvitation(payload: DTOUpdateInvitation): Promise<Invitation> {
    const response = await fetchAPI(
      `items/${payload.itemId}/invitations/${payload.invitationId}/`,
      {
        method: "PATCH",
        body: JSON.stringify(payload),
      }
    );
    const data = await response.json();
    return data;
  }

  async getItemInvitations(itemId: string): Promise<APIList<Invitation>> {
    const response = await fetchAPI(`items/${itemId}/invitations/`);
    const data = await response.json();
    return data;
  }

  async moveItems(ids: string[], parentId: string): Promise<void> {
    for (const id of ids) {
      await this.moveItem(id, parentId);
    }
  }

  async createFolder(data: {
    title: string;
    parentId?: string;
  }): Promise<Item> {
    const { parentId, ...rest } = data;
    const response = await fetchAPI(`items/${parentId}/children/`, {
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

  async createFile(data: {
    parentId: string;
    file: File;
    filename: string;
    progressHandler?: (progress: number) => void;
  }): Promise<Item> {
    const { parentId, file, progressHandler, ...rest } = data;
    const response = await fetchAPI(`items/${parentId}/children/`, {
      method: "POST",
      body: JSON.stringify({
        type: ItemType.FILE,
        ...rest,
      }),
    });
    const item = jsonToItem(await response.json());
    if (!item.policy) {
      throw new Error("No policy found");
    }

    // We don't want to call the progress handler with 100% when the upload is done.
    // We want to wait until the upload-ended endpoint is called.
    const progressHandlerProxy = (progress: number) => {
      if (progress === 100) {
        return;
      }
      progressHandler?.(progress);
    };

    await uploadFile(item.policy, file, (progress) => {
      progressHandlerProxy(progress);
    });

    await fetchAPI(`items/${item.id}/upload-ended/`, {
      method: "POST",
    });

    progressHandler?.(100);

    return item;
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
  progressHandler: (progress: number) => void
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
          Math.floor((progressEvent.loaded / progressEvent.total) * 100)
        );
      }
    });

    xhr.send(file);
  });
