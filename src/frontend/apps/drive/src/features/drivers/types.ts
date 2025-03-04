export enum ItemType {
  FILE = "file",
  FOLDER = "folder",
}

export type Item = {
  id: string;
  name: string;
  type: ItemType;
  lastUpdate: string;
};
