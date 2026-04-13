import { Item } from '@/features/drivers/types';

export type FileJobState =
  | 'pending'
  | 'running'
  | 'done'
  | 'skipped'
  | 'failed';

export type SkipReason = 'already_encrypted' | 'not_encrypted';

export type FileJobRow = {
  id: string;
  title: string;
  path: string;
  state: FileJobState;
  error?: string;
  skipReason?: SkipReason;
};

export type JobPhase =
  | 'discovering'
  | 'validating'
  | 'ready'
  | 'staging'
  | 'committing'
  | 'success'
  | 'failed';

export type FlatNode = {
  item: Item;
  parentId: string | null;
  depth: number;
  pathCrumb: string;
};

export type StagedEncryptFile = {
  itemId: string;
  newFilename: string;
  wrappedKey: ArrayBuffer;
};

export type StagedDecryptFile = {
  itemId: string;
  newFilename: string;
};
