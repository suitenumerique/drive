import { Item, ItemUploadState } from "@/features/drivers/types";
import mimeCalc from "@/assets/files/icons/mime-calc.svg";
import mimeDoc from "@/assets/files/icons/mime-doc.svg";
import mimeImage from "@/assets/files/icons/mime-image.svg";
import mimeOther from "@/assets/files/icons/mime-other.svg";
import mimePdf from "@/assets/files/icons/mime-pdf.svg";
import mimePowerpoint from "@/assets/files/icons/mime-powerpoint.svg";
import mimeAudio from "@/assets/files/icons/mime-audio.svg";
import mimeVideo from "@/assets/files/icons/mime-video.svg";
import mimeSQLite from "@/assets/files/icons/mime-sqlite.svg";
import mimeGrist from "@/assets/files/icons/mime-grist.svg";

import mimeCalcMini from "@/assets/files/icons/mime-calc-mini.svg";
import mimeDocMini from "@/assets/files/icons/mime-doc-mini.svg";
import mimeImageMini from "@/assets/files/icons/mime-image-mini.svg";

import mimePdfMini from "@/assets/files/icons/mime-pdf-mini.svg";
import mimePowerpointMini from "@/assets/files/icons/mime-powerpoint-mini.svg";
import mimeAudioMini from "@/assets/files/icons/mime-audio-mini.svg";
import mimeVideoMini from "@/assets/files/icons/mime-video-mini.svg";
import mimeArchiveMini from "@/assets/files/icons/mime-archive-mini.svg";
import mimeSuspicious from "@/assets/files/icons/suspicious_file.svg";
import mimeSQLiteMini from "@/assets/files/icons/mime-sqlite-mini.svg";
import mimeGristMini from "@/assets/files/icons/mime-grist-mini.svg";

import mimeArchive from "@/assets/files/icons/mime-archive.svg";
import { getExtension, getExtensionFromName } from "../utils/utils";

export enum MimeCategory {
  CALC = "calc",
  DOC = "doc",
  IMAGE = "image",
  OTHER = "other",
  PDF = "pdf",
  POWERPOINT = "powerpoint",
  AUDIO = "audio",
  VIDEO = "video",
  ARCHIVE = "archive",
  SUSPICIOUS = "suspicious",
  SQLITE = "sqlite",
  GRIST = "grist",
}

export const ICONS = {
  mini: {
    [MimeCategory.CALC]: mimeCalcMini,
    [MimeCategory.DOC]: mimeDocMini,
    [MimeCategory.IMAGE]: mimeImageMini,
    [MimeCategory.OTHER]: mimeOther,
    [MimeCategory.PDF]: mimePdfMini,
    [MimeCategory.POWERPOINT]: mimePowerpointMini,
    [MimeCategory.AUDIO]: mimeAudioMini,
    [MimeCategory.VIDEO]: mimeVideoMini,
    [MimeCategory.ARCHIVE]: mimeArchiveMini,
    [MimeCategory.SUSPICIOUS]: mimeSuspicious,
    [MimeCategory.SQLITE]: mimeSQLiteMini,
    [MimeCategory.GRIST]: mimeGristMini,
  },
  normal: {
    [MimeCategory.CALC]: mimeCalc,
    [MimeCategory.DOC]: mimeDoc,
    [MimeCategory.IMAGE]: mimeImage,
    [MimeCategory.OTHER]: mimeOther,
    [MimeCategory.PDF]: mimePdf,
    [MimeCategory.POWERPOINT]: mimePowerpoint,
    [MimeCategory.AUDIO]: mimeAudio,
    [MimeCategory.VIDEO]: mimeVideo,
    [MimeCategory.ARCHIVE]: mimeArchive,
    [MimeCategory.SUSPICIOUS]: mimeSuspicious,
    [MimeCategory.SQLITE]: mimeSQLite,
    [MimeCategory.GRIST]: mimeGrist,
  },
};

export const MIME_TO_FORMAT_TRANSLATION_KEY = {
  [MimeCategory.CALC]: "mime.calc",
  [MimeCategory.DOC]: "mime.doc",
  [MimeCategory.IMAGE]: "mime.image",
  [MimeCategory.OTHER]: "mime.other",
  [MimeCategory.PDF]: "mime.pdf",
  [MimeCategory.POWERPOINT]: "mime.powerpoint",
  [MimeCategory.AUDIO]: "mime.audio",
  [MimeCategory.VIDEO]: "mime.video",
  [MimeCategory.ARCHIVE]: "mime.archive",
  [MimeCategory.SQLITE]: "mime.sqlite",
  [MimeCategory.GRIST]: "mime.grist",
};

export const MIME_MAP = {
  [MimeCategory.CALC]: [
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.oasis.opendocument.spreadsheet",
    "text/csv",
  ],
  [MimeCategory.PDF]: ["application/pdf"],
  [MimeCategory.DOC]: [
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.oasis.opendocument.text",
  ],
  [MimeCategory.POWERPOINT]: [
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "application/vnd.oasis.opendocument.presentation",
  ],
  [MimeCategory.ARCHIVE]: [
    "application/zip",
    "application/x-7z-compressed",
    "application/x-rar-compressed",
    "application/x-tar",
    "application/x-rar",
    "application/octet-stream",
  ],
  [MimeCategory.SQLITE]: [
    "application/x-sqlite3", // deprecated but still exists
    "application/vnd.sqlite3",
  ],
};

// This is used to map mimetypes to categories to get a O(1) lookup
export const MIME_TO_CATEGORY: Record<string, MimeCategory> = {};
Object.entries(MIME_MAP).forEach(([category, mimes]) => {
  mimes.forEach((mime) => {
    MIME_TO_CATEGORY[mime] = category as MimeCategory;
  });
});

export const CALC_EXTENSIONS = ["numbers", "xlsx", "xls"];

// Common file extensions known to the system
export const KNOWN_EXTENSIONS = new Set([
  // Documents
  "doc",
  "docx",
  "docm",
  "odt",
  "rtf",
  "txt",
  "pdf",
  // Spreadsheets
  "xls",
  "xlsx",
  "xlsm",
  "ods",
  "csv",
  "numbers",
  // Presentations
  "ppt",
  "pptx",
  "pptm",
  "odp",
  // Images
  "jpg",
  "jpeg",
  "png",
  "gif",
  "bmp",
  "svg",
  "webp",
  "ico",
  "tiff",
  "tif",
  "heic",
  "heif",
  // Audio
  "mp3",
  "wav",
  "flac",
  "aac",
  "ogg",
  "oga",
  "wma",
  "m4a",
  // Video
  "mp4",
  "avi",
  "mov",
  "wmv",
  "flv",
  "webm",
  "mkv",
  "m4v",
  "3gp",
  // Archives
  "zip",
  "rar",
  "7z",
  "tar",
  "gz",
  "bz2",
  "xz",
  // Database
  "db",
  "sqlite",
  "sqlite3",
  "grist",
  // Other common
  "html",
  "htm",
  "xml",
  "json",
  "js",
  "ts",
  "css",
  "scss",
  "py",
  "java",
  "cpp",
  "c",
  "h",
  "php",
  "rb",
  "go",
  "rs",
  "md",
  "yaml",
  "yml",
]);

export const getMimeCategory = (
  mimetype: string,
  extension?: string | null
): MimeCategory => {
  // Special case: some calc files have application/zip mimetype. For those we should check their extension too.
  // Otherwise they will be shown as zip files.
  if (extension && CALC_EXTENSIONS.includes(extension)) {
    return MimeCategory.CALC;
  }

  // Special case: a SQLITE file that has a .grist extension is a grist file
  if (mimetype === "application/vnd.sqlite3" && extension === "grist") {
    return MimeCategory.GRIST;
  }

  if (MIME_TO_CATEGORY[mimetype]) {
    return MIME_TO_CATEGORY[mimetype];
  }
  if (mimetype?.startsWith("image/")) {
    return MimeCategory.IMAGE;
  }
  if (mimetype?.startsWith("audio/")) {
    return MimeCategory.AUDIO;
  }
  if (mimetype?.startsWith("video/")) {
    return MimeCategory.VIDEO;
  }

  return MimeCategory.OTHER;
};

export const getItemMimeCategory = (item: Item): MimeCategory => {
  const mimetype = item.mimetype;
  const extension = getExtension(item);
  const uploadState = item.upload_state;
  if (uploadState === ItemUploadState.SUSPICIOUS) {
    return MimeCategory.SUSPICIOUS;
  }

  if (!mimetype) {
    return MimeCategory.OTHER;
  }

  return getMimeCategory(mimetype, extension);
};

export const getFormatTranslationKey = (item: Item) => {
  const category = getItemMimeCategory(item);
  if (category === MimeCategory.SUSPICIOUS) {
    return "mime.suspicious";
  }
  return MIME_TO_FORMAT_TRANSLATION_KEY[category];
};

/**
 * Validates if a string is a known file extension.
 * Checks if the extension exists in the KNOWN_EXTENSIONS set.
 */
const isValidExtension = (extension: string): boolean => {
  if (!extension || extension.length === 0) {
    return false;
  }

  // Check if extension is in lowercase in the known extensions set
  return KNOWN_EXTENSIONS.has(extension.toLowerCase());
};

/**
 * This function removes the file extension from the filename.
 * It only removes extensions that are in the KNOWN_EXTENSIONS set.
 */
export const removeFileExtension = (filename: string) => {
  if (!filename) {
    return filename;
  }

  // Handle hidden files (starting with a dot)
  if (filename.startsWith(".")) {
    return filename;
  }

  const extension = getExtensionFromName(filename);
  if (!extension) {
    return filename; // No extension found
  }

  // Only remove if it's a valid extension
  if (!isValidExtension(extension)) {
    return filename;
  }

  // Remove only the extension (including the dot)
  const extensionLength = extension.length + 1; // +1 for the dot
  return filename.slice(0, -extensionLength);
};
