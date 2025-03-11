export enum ItemType {
  FILE = "file",
  FOLDER = "folder",
}

export type Item = {
  id: string;
  title: string;
  type: ItemType;
  updated_at: Date;
  children?: Item[];
};
