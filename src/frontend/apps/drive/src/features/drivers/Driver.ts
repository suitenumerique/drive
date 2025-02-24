import { Item } from "./types";

export abstract class Driver {
  abstract getItems(path: string): Promise<Item[]>;
}
