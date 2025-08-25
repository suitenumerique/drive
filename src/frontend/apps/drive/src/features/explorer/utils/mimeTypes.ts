import { Item, ItemUploadState } from "@/features/drivers/types";
import mimeCalc from "@/assets/files/icons/mime-calc.svg";
import mimeDoc from "@/assets/files/icons/mime-doc.svg";
import mimeImage from "@/assets/files/icons/mime-image.svg";
import mimeOther from "@/assets/files/icons/mime-other.svg";
import mimePdf from "@/assets/files/icons/mime-pdf.svg";
import mimePowerpoint from "@/assets/files/icons/mime-powerpoint.svg";
import mimeAudio from "@/assets/files/icons/mime-audio.svg";
import mimeVideo from "@/assets/files/icons/mime-video.svg";

import mimeCalcMini from "@/assets/files/icons/mime-calc-mini.svg";
import mimeDocMini from "@/assets/files/icons/mime-doc-mini.svg";
import mimeImageMini from "@/assets/files/icons/mime-image-mini.svg";

import mimePdfMini from "@/assets/files/icons/mime-pdf-mini.svg";
import mimePowerpointMini from "@/assets/files/icons/mime-powerpoint-mini.svg";
import mimeAudioMini from "@/assets/files/icons/mime-audio-mini.svg";
import mimeVideoMini from "@/assets/files/icons/mime-video-mini.svg";
import mimeArchiveMini from "@/assets/files/icons/mime-archive-mini.svg";
import mimeSuspicious from "@/assets/files/icons/suspicious_file.svg";

import mimeArchive from "@/assets/files/icons/mime-archive.svg";
import { getExtension } from "../utils/utils";

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
}

export const MIME_TO_ICON = {
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
};

export const MIME_TO_ICON_MINI = {
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
};

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
};

export const MIME_MAP = {
  [MimeCategory.CALC]: [
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "text/csv",
  ],
  [MimeCategory.PDF]: ["application/pdf"],
  [MimeCategory.DOC]: [
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  ],
  [MimeCategory.POWERPOINT]: [
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
  ],
  [MimeCategory.ARCHIVE]: [
    "application/zip",
    "application/x-7z-compressed",
    "application/x-rar-compressed",
    "application/x-tar",
    "application/x-rar",
    "application/octet-stream",
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

export const getMimeCategory = (
  mimetype: string,
  extension?: string | null
): MimeCategory => {
  // Special case: some calc files have application/zip mimetype. For those we should check their extension too.
  // Otherwise they will be shown as zip files.
  if (
    mimetype === "application/zip" &&
    extension &&
    CALC_EXTENSIONS.includes(extension)
  ) {
    return MimeCategory.CALC;
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
 * This function removes the file extension from the filename.
 */
export const removeFileExtension = (filename: string) => {
  const lastDotIndex = filename.lastIndexOf(".");
  if (lastDotIndex === -1) {
    return filename; // No extension found
  }
  return filename.substring(0, lastDotIndex);
};
