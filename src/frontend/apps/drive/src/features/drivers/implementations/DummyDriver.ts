import { Driver } from "../Driver";
import { Item, ItemType } from "../types";

export class DummyDriver extends Driver {
  async getItems(): Promise<Item[]> {
    return [
      {
        id: "1",
        title: "Mon Espace",
        type: ItemType.FOLDER,
        lastUpdate: new Date().toISOString(),
      },
    ];
  }

  async getItem(id: string): Promise<Item> {
    return {
      id: "1",
      title: "Mon Espace",
      type: ItemType.FOLDER,
      lastUpdate: new Date().toISOString(),
    };
  }

  async createFolder(data: { title: string }): Promise<Item> {
    return {
      id: "1",
      title: data.title,
      type: ItemType.FOLDER,
      lastUpdate: new Date().toISOString(),
    };
  }
}
