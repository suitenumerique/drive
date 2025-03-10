import { fetchAPI } from "@/features/api/fetchApi";
import { Driver } from "../Driver";
import { Item, ItemType } from "../types";

export class StandardDriver extends Driver {
  async getItems(filters = {}): Promise<Item[]> {
    const response = await fetchAPI(`items/`, {
      params: filters,
    });
    const data = await response.json();
    return data.results;
  }

  async getItem(id: string): Promise<Item> {
    const response = await fetchAPI(`items/${id}/`);
    const data = await response.json();
    return data;
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
    return item;
  }
}
