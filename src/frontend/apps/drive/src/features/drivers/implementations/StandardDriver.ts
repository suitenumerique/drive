import { fetchAPI } from "@/features/api/fetchApi";
import { Driver, ItemFilters } from "../Driver";
import { Item, ItemType } from "../types";

export class StandardDriver extends Driver {
  async getItems(filters = {}): Promise<Item[]> {
    const response = await fetchAPI(`items/`, {
      params: filters,
    });
    const data = await response.json();
    return jsonToItems(data.results);
  }

  async getTrashItems(): Promise<Item[]> {
    const response = await fetchAPI(`items/trashbin/?page_size=100000`);
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

  async getChildren(id: string, filters?: ItemFilters): Promise<Item[]> {
    const params = {
      page_size: "100000",
      ordering: "-type,-created_at",
      ...(filters ? filters : {}),
    };
    const response = await fetchAPI(`items/${id}/children/`, {
      params,
    });
    const data = await response.json();
    return jsonToItems(data.results);
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

    const { url, fields } = item.policy!;
    const formData = new FormData();

    // Add all the policy fields to the form data
    Object.entries(fields).forEach(([key, value]) => {
      formData.append(key, value);
    });
    formData.append("file", file);

    let urlObject = new URL(url);
    if (process.env["NEXT_PUBLIC_S3_DOMAIN_REPLACE"]) {
      urlObject = new URL(
        urlObject.pathname,
        process.env["NEXT_PUBLIC_S3_DOMAIN_REPLACE"]
      );
    }

    await uploadFile(urlObject.toString(), formData, (progress) => {
      progressHandler?.(progress);
    });

    await fetchAPI(`items/${item.id}/upload-ended/`, {
      method: "POST",
    });

    return item;
  }

  async deleteItems(ids: string[]): Promise<void> {
    for (const id of ids) {
      await fetchAPI(`items/${id}/`, {
        method: "DELETE",
      });
    }
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
  formData: FormData,
  progressHandler: (progress: number) => void
) =>
  new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", url);

    xhr.addEventListener("error", reject);
    xhr.addEventListener("abort", reject);

    xhr.addEventListener("readystatechange", () => {
      if (xhr.readyState === 4) {
        if (xhr.status === 204) {
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

    xhr.send(formData);
  });
