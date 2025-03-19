export enum ItemType {
  FILE = "file",
  FOLDER = "folder",
}

export type Item = {
  id: string;
  title: string;
  filename: string;
  type: ItemType;
  upload_state: string;
  updated_at: Date;
  children?: Item[];
  url?: string;
  mimetype?: string;
  policy?: {
    url: string;
    fields: {
      AWSAccessKeyId: string;
      acl: string;
      policy: string;
      key: string;
      signature: string;
    };
  };
};
