import { CellContext } from "@tanstack/react-table";
import { Item, ItemUploadState, LinkReach } from "@/features/drivers/types";
import { useEffect, useMemo, useRef, useState } from "react";
import { Draggable } from "@/features/explorer/components/Draggable";
import { Tooltip } from "@gouvfr-lasuite/cunningham-react";
import { ItemIcon } from "@/features/explorer/components/icons/ItemIcon";
import { useDisableDragGridItem } from "@/features/explorer/components/embedded-explorer/hooks";
import { removeFileExtension } from "../../utils/mimeTypes";
import { Icon, IconSize } from "@gouvfr-lasuite/ui-kit";
import { Spinner } from "@/features/ui/components/spinner/Spinner";
import { useEmbeddedExplorerGirdContext } from "./EmbeddedExplorerGrid";
import { useTranslation } from "react-i18next";
import { useDuplicatingItemPoll } from "../../hooks/useDuplicatingItemPoll";
import clsx from "clsx";
export type EmbeddedExplorerGridNameCellProps = CellContext<Item, string> & {
  children?: React.ReactNode;
};

export const EmbeddedExplorerGridNameCell = (
  params: EmbeddedExplorerGridNameCellProps,
) => {
  const item = params.row.original;
  const { t } = useTranslation();
  const ref = useRef<HTMLSpanElement>(null);
  const [isOverflown, setIsOverflown] = useState(false);
  const { selectedItemsMap, disableItemDragAndDrop } =
    useEmbeddedExplorerGirdContext();
  const isSelected = !!selectedItemsMap[item.id];
  const isDuplicating = item.upload_state === ItemUploadState.DUPLICATING;
  useDuplicatingItemPoll(item);

  const disableDrag = useDisableDragGridItem(item);

  const renderTitle = () => {
    // We need to have the element holding the ref nested because the Tooltip component
    // seems to make the top-most children ref null.
    return (
      <Draggable
        id={params.cell.id + "-title"}
        item={item}
        className="explorer__grid__item__name__title-wrapper"
        disabled={isDuplicating || disableItemDragAndDrop || isSelected} // If it's selected then we can drag on the entire cell
      >
        <div className="explorer__grid__item__name__title-wrapper">
          <span
            className={clsx("explorer__grid__item__name__text", {
              "explorer__grid__item__name--duplicating-text": isDuplicating,
            })}
            ref={ref}
          >
            {removeFileExtension(item.title)}
            {isDuplicating && (
              <span className="explorer__grid__item__name__duplicating-label">
                {" "}
                ({t("explorer.item.duplicating")})
              </span>
            )}
            {params.children}
          </span>
        </div>
      </Draggable>
    );
  };

  useEffect(() => {
    const checkOverflow = () => {
      const element = ref.current;
      // Should always be defined, but just in case.
      if (element) {
        setIsOverflown(element.scrollWidth > element.clientWidth);
      }
    };
    checkOverflow();

    window.addEventListener("resize", checkOverflow);
    return () => {
      window.removeEventListener("resize", checkOverflow);
    };
  }, [item.title]);

  const rightIcon = useMemo(() => {
    let icon: string | null = null;

    if (item.computed_link_reach === LinkReach.PUBLIC) {
      icon = "public";
    } else if (item.nb_accesses && item.nb_accesses > 1) {
      icon = "people";
    }
    return icon;
  }, [item.computed_link_reach, item.link_reach, item.nb_accesses]);

  return (
    <Draggable
      id={params.cell.id}
      item={item}
      disabled={isDuplicating || disableDrag}
    >
      <div
        className={`explorer__grid__item__name${isDuplicating ? " explorer__grid__item__name--duplicating" : ""}`}
      >
        {isDuplicating ? (
          <div className="explorer__grid__item__name__spinner-container">
            <Spinner size="md" />
          </div>
        ) : (
          <ItemIcon key={item.id} item={item} size={IconSize.LARGE} />
        )}
        {isOverflown ? (
          <Tooltip content={item.title}>{renderTitle()}</Tooltip>
        ) : (
          renderTitle()
        )}
        {rightIcon && (
          <Icon
            name={rightIcon}
            size={IconSize.SMALL}
            color="var(--c--contextuals--content--semantic--neutral--tertiary)"
          />
        )}
      </div>
    </Draggable>
  );
};
