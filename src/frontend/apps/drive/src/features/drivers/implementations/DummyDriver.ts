import { Driver } from "../Driver";
import { Item, ItemType } from "../types";

export class DummyDriver extends Driver {
  async getItems(): Promise<Item[]> {
    return [
      {
        id: "1",
        name: "Mon Espace",
        type: ItemType.FOLDER,
      },
    ];
  }
}
