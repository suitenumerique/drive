import { Item, ItemType } from "./types";

export abstract class Driver {
  abstract getItems(filters?: { type?: ItemType }): Promise<Item[]>;
  abstract getItem(id: string): Promise<Item>;
  abstract createFolder(data: { title: string }): Promise<Item>;
}
