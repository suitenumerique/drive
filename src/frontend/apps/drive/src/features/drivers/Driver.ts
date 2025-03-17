import { Item, ItemType } from "./types";

export abstract class Driver {
  abstract getItems(filters?: { type?: ItemType }): Promise<Item[]>;
  abstract getItem(id: string): Promise<Item>;
  abstract getChildren(id: string): Promise<Item[]>;
  abstract getTree(id: string): Promise<Item>;
  abstract createFolder(data: { title: string }): Promise<Item>;
  abstract createFile(data: {
    parentId: string;
    filename: string;
  }): Promise<Item>;
  abstract deleteItems(ids: string[]): Promise<void>;
}
