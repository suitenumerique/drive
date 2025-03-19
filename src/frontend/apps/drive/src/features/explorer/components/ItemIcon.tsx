import { Item, ItemType } from "@/features/drivers/types";
import mimeCalc from "@/assets/files/icons/mime-calc.svg";
import mimeDoc from "@/assets/files/icons/mime-doc.svg";
import mimeImage from "@/assets/files/icons/mime-image.svg";
import mimeOther from "@/assets/files/icons/mime-other.svg";
import mimePdf from "@/assets/files/icons/mime-pdf.svg";
import mimePowerpoint from "@/assets/files/icons/mime-powerpoint.svg";
import mimeAudio from "@/assets/files/icons/mime-audio.svg";
import mimeVideo from "@/assets/files/icons/mime-video.svg";
import mimeArchive from "@/assets/files/icons/mime-archive.svg";
import folderIcon from "@/assets/folder/folder.svg";
import { getExtension } from "../utils/utils";

enum MimeCategory {
  CALC = "calc",
  DOC = "doc",
  IMAGE = "image",
  OTHER = "other",
  PDF = "pdf",
  POWERPOINT = "powerpoint",
  AUDIO = "audio",
  VIDEO = "video",
  ARCHIVE = "archive",
}

const MIME_TO_ICON = {
  [MimeCategory.CALC]: mimeCalc,
  [MimeCategory.DOC]: mimeDoc,
  [MimeCategory.IMAGE]: mimeImage,
  [MimeCategory.OTHER]: mimeOther,
  [MimeCategory.PDF]: mimePdf,
  [MimeCategory.POWERPOINT]: mimePowerpoint,
  [MimeCategory.AUDIO]: mimeAudio,
  [MimeCategory.VIDEO]: mimeVideo,
  [MimeCategory.ARCHIVE]: mimeArchive,
};

export const ItemIcon = ({ item }: { item: Item }) => {
  if (item.type === ItemType.FOLDER) {
    // eslint-disable-next-line @next/next/no-img-element
    return <img src={folderIcon.src} alt="" />;
  }
  const mimeCategory = getMimeCategory(item);
  // eslint-disable-next-line @next/next/no-img-element
  return <img src={MIME_TO_ICON[mimeCategory].src} alt="" />;
};

const MIME_MAP = {
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
const MIME_TO_CATEGORY: Record<string, MimeCategory> = {};
Object.entries(MIME_MAP).forEach(([category, mimes]) => {
  mimes.forEach((mime) => {
    MIME_TO_CATEGORY[mime] = category as MimeCategory;
  });
});

const CALC_EXTENSIONS = ["numbers", "xlsx", "xls"];

export const getMimeCategory = (item: Item): MimeCategory => {
  // Special case: some calc files have application/zip mimetype. For those we should check their extension too.
  // Otherwise they will be shown as zip files.
  const extension = getExtension(item);
  if (
    item.mimetype === "application/zip" &&
    extension &&
    CALC_EXTENSIONS.includes(extension)
  ) {
    return MimeCategory.CALC;
  }

  if (MIME_TO_CATEGORY[item.mimetype!]) {
    return MIME_TO_CATEGORY[item.mimetype!];
  }
  if (item.mimetype?.startsWith("image/")) {
    return MimeCategory.IMAGE;
  }
  if (item.mimetype?.startsWith("audio/")) {
    return MimeCategory.AUDIO;
  }
  if (item.mimetype?.startsWith("video/")) {
    return MimeCategory.VIDEO;
  }

  return MimeCategory.OTHER;
};
