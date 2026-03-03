export type FolderMode = "files_only" | "folders_first" | "mixed";

export type ViewConfig = {
  defaultOrdering: string;
  folderMode: FolderMode;
};
