import { fetchAPI } from "@/features/api/fetchApi";
import { Driver } from "../Driver";
import { Item } from "../types";

export class StandardDriver extends Driver {
  async getItems(): Promise<Item[]> {
    const response = await fetchAPI(`items/`);
    const data = await response.json();
    return data.results;
  }
}
