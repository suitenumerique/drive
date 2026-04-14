/**
 * Types for the OnlyOffice client-side bridge.
 *
 * These interfaces mirror the connectMockServer() API that OnlyOffice exposes
 * when loaded without a Document Server.
 */

/** A single OnlyOffice change/patch */
export interface OOChange {
  docid: string;
  change: string; // JSON-stringified change data
  time: number;
  user: string;
  useridoriginal: string;
}

/** A participant in the collaboration session */
export interface OOParticipant {
  id: string;
  idOriginal: string;
  username: string;
  // Empty string so OO computes _userId = config.user.id + '' = config.user.id.
  // Without this, OO appends the index to the user id (sub_1) but comments
  // embed config.user.id directly (sub) — the mismatch breaks comment author
  // attribution at the receiver.
  indexUser: string;
  connectionId: string;
  isCloseCoAuthoring: boolean;
  view: boolean;
}

/** Return type for getParticipants() */
export interface OOParticipantList {
  index: string;
  list: OOParticipant[];
}

/** Events that OnlyOffice sends via onMessage/fromOOHandler */
export type OOEventType =
  | 'saveChanges'
  | 'getLock'
  | 'cursor'
  | 'isSaveLock'
  | 'getMessages'
  | 'unSaveLock'
  | 'unLockDocument'
  | 'authChanges'
  | 'auth'
  | 'authChangesAck'
  | 'clientLog'
  | 'saveLock'
  | 'savePartChanges'
  | 'releaseLock'
  | 'message'
  | 'forceSaveStart'
  | 'forceSave'
  | 'connectState'
  | 'meta';

/** Message from OnlyOffice editor */
export interface OOMessage {
  type: OOEventType;
  changes?: OOChange[];
  locks?: unknown[];
  cursor?: unknown;
  [key: string]: unknown;
}

/** Callbacks passed to connectMockServer() */
export interface MockServerCallbacks {
  onMessage: (msg: OOMessage) => void;
  getParticipants: () => OOParticipantList;
  onAuth: () => void;
  getImageURL: (name: string) => Promise<string>;
  getInitialChanges: () => OOChange[];
}

/** OnlyOffice editor configuration */
export interface OOConfig {
  document: {
    fileType: string;
    key: string;
    title: string;
    url: string; // Blob URL for the .bin content
  };
  documentType: 'word' | 'cell' | 'slide';
  editorConfig: {
    mode: 'edit' | 'view';
    user: {
      id: string;
      name: string;
    };
    lang: string;
    customization?: {
      compactToolbar: boolean;
      forcesave: boolean;
      autosave?: boolean;
    };
    permissions?: {
      chat?: boolean;
      comment?: boolean;
      download?: boolean;
      edit?: boolean;
      print?: boolean;
    };
  };
  events: {
    onAppReady?: () => void;
    onDocumentReady?: () => void;
    onError?: (event: { data: unknown }) => void;
  };
}

/** Checkpoint data (saved state of the document) */
export interface Checkpoint {
  /** Encrypted file content on S3 */
  s3Key: string;
  /** Number of patches applied at checkpoint time */
  patchIndex: number;
  /** OnlyOffice format version */
  version: number;
  /** Timestamp of the checkpoint */
  timestamp: number;
}

/** Collaboration state shared between users */
export interface CollaborationState {
  /** Active user IDs with their OO indices */
  ids: Record<string, { ooid: number; index: number; netflux: string }>;
  /** Active locks (cell/range locks for spreadsheets) */
  locks: Record<string, unknown>;
  /** Which user currently holds the save lock */
  saveLock: number | null;
}

/** Map from file extension to OnlyOffice documentType (as used by CryptPad) */
export const EXTENSION_TO_DOC_TYPE: Record<
  string,
  'text' | 'spreadsheet' | 'presentation'
> = {
  docx: 'text',
  doc: 'text',
  odt: 'text',
  txt: 'text',
  html: 'text',
  xlsx: 'spreadsheet',
  xls: 'spreadsheet',
  ods: 'spreadsheet',
  csv: 'spreadsheet',
  pptx: 'presentation',
  ppt: 'presentation',
  odp: 'presentation',
};

/** Map from file extension to the MS Office fileType OnlyOffice expects */
export const EXTENSION_TO_OO_FILE_TYPE: Record<string, string> = {
  docx: 'docx',
  doc: 'docx',
  odt: 'docx',
  txt: 'docx',
  html: 'docx',
  xlsx: 'xlsx',
  xls: 'xlsx',
  ods: 'xlsx',
  csv: 'xlsx',
  pptx: 'pptx',
  ppt: 'pptx',
  odp: 'pptx',
};

// --- Mimetype-based mappings (preferred over extension-based) ---

const OFFICE_MIMES = {
  ODT: 'application/vnd.oasis.opendocument.text',
  ODS: 'application/vnd.oasis.opendocument.spreadsheet',
  ODP: 'application/vnd.oasis.opendocument.presentation',
  DOCX: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  XLSX: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  PPTX: 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
  DOC: 'application/msword',
  XLS: 'application/vnd.ms-excel',
  PPT: 'application/vnd.ms-powerpoint',
  TXT: 'text/plain',
  CSV: 'text/csv',
} as const;

/** Map mimetype → OnlyOffice documentType (word/cell/slide as per api-orig.js) */
export const MIME_TO_DOC_TYPE: Record<string, 'word' | 'cell' | 'slide'> = {
  [OFFICE_MIMES.ODT]: 'word',
  [OFFICE_MIMES.DOCX]: 'word',
  [OFFICE_MIMES.DOC]: 'word',
  [OFFICE_MIMES.TXT]: 'word',
  [OFFICE_MIMES.ODS]: 'cell',
  [OFFICE_MIMES.XLSX]: 'cell',
  [OFFICE_MIMES.XLS]: 'cell',
  [OFFICE_MIMES.CSV]: 'cell',
  [OFFICE_MIMES.ODP]: 'slide',
  [OFFICE_MIMES.PPTX]: 'slide',
  [OFFICE_MIMES.PPT]: 'slide',
};

/** Map mimetype → OnlyOffice fileType (the MS format OnlyOffice uses internally) */
export const MIME_TO_OO_FILE_TYPE: Record<string, string> = {
  [OFFICE_MIMES.ODT]: 'docx',
  [OFFICE_MIMES.DOCX]: 'docx',
  [OFFICE_MIMES.DOC]: 'docx',
  [OFFICE_MIMES.TXT]: 'docx',
  [OFFICE_MIMES.ODS]: 'xlsx',
  [OFFICE_MIMES.XLSX]: 'xlsx',
  [OFFICE_MIMES.XLS]: 'xlsx',
  [OFFICE_MIMES.CSV]: 'xlsx',
  [OFFICE_MIMES.ODP]: 'pptx',
  [OFFICE_MIMES.PPTX]: 'pptx',
  [OFFICE_MIMES.PPT]: 'pptx',
};

/** Map mimetype → x2t document type for intermediate conversion */
export const MIME_TO_X2T_TYPE: Record<string, string> = {
  [OFFICE_MIMES.ODT]: 'doc',
  [OFFICE_MIMES.DOCX]: 'doc',
  [OFFICE_MIMES.DOC]: 'doc',
  [OFFICE_MIMES.TXT]: 'doc',
  [OFFICE_MIMES.ODS]: 'sheet',
  [OFFICE_MIMES.XLSX]: 'sheet',
  [OFFICE_MIMES.XLS]: 'sheet',
  [OFFICE_MIMES.CSV]: 'sheet',
  [OFFICE_MIMES.ODP]: 'presentation',
  [OFFICE_MIMES.PPTX]: 'presentation',
  [OFFICE_MIMES.PPT]: 'presentation',
};

/** Map mimetype → file extension (for x2t filename) */
export const MIME_TO_EXTENSION: Record<string, string> = {
  [OFFICE_MIMES.ODT]: 'odt',
  [OFFICE_MIMES.DOCX]: 'docx',
  [OFFICE_MIMES.DOC]: 'doc',
  [OFFICE_MIMES.TXT]: 'txt',
  [OFFICE_MIMES.ODS]: 'ods',
  [OFFICE_MIMES.XLSX]: 'xlsx',
  [OFFICE_MIMES.XLS]: 'xls',
  [OFFICE_MIMES.CSV]: 'csv',
  [OFFICE_MIMES.ODP]: 'odp',
  [OFFICE_MIMES.PPTX]: 'pptx',
  [OFFICE_MIMES.PPT]: 'ppt',
};

// --- Extension-based mappings (legacy, used by some components) ---

/** Map from file extension to the intermediate format x2t needs */
export const EXTENSION_TO_X2T_TYPE: Record<string, string> = {
  docx: 'doc',
  doc: 'doc',
  odt: 'doc',
  txt: 'doc',
  html: 'doc',
  xlsx: 'sheet',
  xls: 'sheet',
  ods: 'sheet',
  csv: 'sheet',
  pptx: 'presentation',
  ppt: 'presentation',
  odp: 'presentation',
};
