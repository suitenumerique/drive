/**
 * Types for the OnlyOffice client-side bridge.
 *
 * These interfaces mirror the connectMockServer() API that OnlyOffice exposes
 * when loaded without a Document Server. CryptPad's inner.js documents this
 * interface implicitly through its implementation.
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
  indexUser: number;
  connectionId: string;
  isCloseCoAuthoring: boolean;
  view: boolean;
}

/** Return type for getParticipants() */
export interface OOParticipantList {
  index: number;
  list: OOParticipant[];
}

/** Events that OnlyOffice sends via onMessage/fromOOHandler */
export type OOEventType =
  | "saveChanges"
  | "getLock"
  | "cursor"
  | "isSaveLock"
  | "getMessages"
  | "unSaveLock"
  | "unLockDocument"
  | "authChanges";

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
  onMessage: (handler: (msg: OOMessage) => void) => void;
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
  documentType: "word" | "cell" | "slide";
  editorConfig: {
    mode: "edit" | "view";
    user: {
      id: string;
      name: string;
    };
    lang: string;
    customization?: {
      chat: boolean;
      compactToolbar: boolean;
      forcesave: boolean;
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
  ids: Record<
    string,
    { ooid: number; index: number; netflux: string }
  >;
  /** Active locks (cell/range locks for spreadsheets) */
  locks: Record<string, unknown>;
  /** Which user currently holds the save lock */
  saveLock: number | null;
}

/** Map from file extension to OnlyOffice document type */
export const EXTENSION_TO_DOC_TYPE: Record<string, "word" | "cell" | "slide"> = {
  docx: "word",
  doc: "word",
  odt: "word",
  txt: "word",
  html: "word",
  xlsx: "cell",
  xls: "cell",
  ods: "cell",
  csv: "cell",
  pptx: "slide",
  ppt: "slide",
  odp: "slide",
};

/** Map from file extension to the intermediate format x2t needs */
export const EXTENSION_TO_X2T_TYPE: Record<string, string> = {
  docx: "doc",
  doc: "doc",
  odt: "doc",
  txt: "doc",
  html: "doc",
  xlsx: "sheet",
  xls: "sheet",
  ods: "sheet",
  csv: "sheet",
  pptx: "presentation",
  ppt: "presentation",
  odp: "presentation",
};
