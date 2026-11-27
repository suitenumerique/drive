import { useState } from "react";
import clsx from "clsx";
import { IconSize } from "@gouvfr-lasuite/ui-components";
import { Item, ItemUploadState } from "@/features/drivers/types";
import { ItemIcon } from "./ItemIcon";

type ItemThumbnailProps = {
  item: Item;
  // BEM block of the container, which gets a `--thumbnail` modifier when an
  // image is displayed instead of the icon.
  className: string;
};

/**
 * Displays the rendered thumbnail of an item, or the preview of an image,
 * falling back to its large icon when there is none or it fails to load.
 */
export const ItemThumbnail = ({ item, className }: ItemThumbnailProps) => {
  // The URL that failed rather than a flag, so that a new render is tried again.
  const [failedSrc, setFailedSrc] = useState<string>();
  // Images are shown from the file itself, which must have passed the malware
  // analysis: a suspicious one keeps its warning icon.
  const src =
    item.url_thumbnail ??
    (item.mimetype?.startsWith("image/") &&
    item.upload_state === ItemUploadState.READY
      ? item.url_preview
      : undefined);

  if (!src || src === failedSrc) {
    return (
      <div className={className}>
        <ItemIcon item={item} size={IconSize.X_LARGE} />
      </div>
    );
  }

  return (
    <div className={clsx(className, `${className}--thumbnail`)}>
      <img
        src={src}
        // Decorative: the item title is always displayed next to it.
        alt=""
        onError={() => setFailedSrc(src)}
      />
    </div>
  );
};
