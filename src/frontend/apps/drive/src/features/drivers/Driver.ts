import { Item, ItemType } from "./types";


export type ItemFilters = {
  type?: ItemType;
  
};

export abstract class Driver {
  abstract getItems(filters?: ItemFilters): Promise<Item[]>;
  abstract getItem(id: string): Promise<Item>;
  abstract updateItem(item: Partial<Item>): Promise<Item>;
  abstract moveItem(id: string, parentId: string): Promise<void>;
  abstract moveItems(ids: string[], parentId: string): Promise<void>;
  abstract getChildren(id: string, filters?: ItemFilters): Promise<Item[]>;
  abstract getTree(id: string): Promise<Item>;
  abstract createFolder(data: { title: string }): Promise<Item>;
  abstract createWorkspace(data: {
    title: string;
    description: string;
  }): Promise<Item>;
  abstract updateWorkspace(item: Partial<Item>): Promise<Item>;
  abstract deleteWorkspace(id: string): Promise<void>;
  abstract createFile(data: {
    parentId: string;
    filename: string;
  }): Promise<Item>;
  abstract deleteItems(ids: string[]): Promise<void>;
}
