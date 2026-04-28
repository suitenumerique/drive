import { useCallback, useEffect, useRef, useState } from "react";
import { Thumbnail } from "react-pdf";
import { AutoSizer, List } from "react-virtualized";
import type { ListRowRenderer } from "react-virtualized";
import {
  OPEN_DELAY,
  THUMBNAIL_GAP,
  THUMBNAIL_LABEL_SPACE,
  THUMBNAIL_WIDTH,
  TRANSITION_DELAY,
} from "./pdfConsts";
import { FALLBACK_RATIO, type PageDimensionsMap } from "./usePdfPageDimensions";

interface PdfThumbnailSidebarProps {
  numPages: number;
  currentPage: number;
  goToPage: (page: number) => void;
  isOpen: boolean;
  pageDimensions: PageDimensionsMap;
  requestPageDimension: (page: number) => void;
}

// Two-phase mount/unmount to allow CSS transitions to play out:
// Opening: mount immediately (unmount=false), then defer isOpenProxy=true
//   so the DOM is present before the "open" class triggers the transition.
// Closing: remove the "open" class first (isOpenProxy=false), wait for the
//   transition to finish (TRANSITION_DELAY), then unmount the component.
// When closed the component is not mounted, which is better for performance
// as this component is quite heavy and is not needed when closed.
export function PdfThumbnailSidebar(props: PdfThumbnailSidebarProps) {
  const [unmount, setUnmount] = useState(true);
  const [isOpenProxy, setIsOpenProxy] = useState(props.isOpen);

  useEffect(() => {
    let timer: ReturnType<typeof setTimeout>;
    if (props.isOpen) {
      setUnmount(false);
      timer = setTimeout(() => setIsOpenProxy(true), OPEN_DELAY);
    } else {
      setIsOpenProxy(false);
      // The 1.1 is to allow for the transition to finish.
      // It is a safety margin to avoid the component being unmounted too early.
      timer = setTimeout(() => setUnmount(true), TRANSITION_DELAY * 1.1);
    }
    return () => clearTimeout(timer);
  }, [props.isOpen]);

  if (unmount) {
    return null;
  }

  return <PdfThumbnailSidebarContent {...props} isOpen={isOpenProxy} />;
}

export function PdfThumbnailSidebarContent({
  numPages,
  currentPage,
  goToPage,
  isOpen,
  pageDimensions,
  requestPageDimension,
}: PdfThumbnailSidebarProps) {
  const listRef = useRef<List>(null);
  // When true, the next currentPage change came from a thumbnail click
  // and should not trigger an auto-scroll of the sidebar.
  const isClickNavRef = useRef(false);
  // Scroll to the current page on first render, then clear so the prop
  // no longer forces scroll position on subsequent renders.
  const [initialScrollIndex, setInitialScrollIndex] = useState<
    number | undefined
  >(currentPage - 1);

  // Auto-scroll active thumbnail into view (only for scroll-initiated changes)
  useEffect(() => {
    if (!listRef.current) return;
    if (isClickNavRef.current) {
      isClickNavRef.current = false;
      return;
    }
    listRef.current.scrollToRow(currentPage - 1);
  }, [currentPage]);

  const getRatio = useCallback(
    (index: number) => {
      const d = pageDimensions.get(index + 1);
      return d ? d.h / d.w : FALLBACK_RATIO;
    },
    [pageDimensions],
  );

  const rowHeight = useCallback(
    ({ index }: { index: number }) => {
      const thumbH = THUMBNAIL_WIDTH * getRatio(index);
      const base = thumbH + THUMBNAIL_LABEL_SPACE + THUMBNAIL_GAP;
      // Every row reserves a gap above via paddingTop. The last row also
      // reserves one below so the final thumbnail has matching breathing
      // room at the bottom of the sidebar.
      return index === numPages - 1 ? base + THUMBNAIL_GAP : base;
    },
    [getRatio, numPages],
  );

  // Invalidate react-virtualized's row-height cache when dimensions update.
  useEffect(() => {
    listRef.current?.recomputeRowHeights();
  }, [pageDimensions, numPages]);

  const handleRowsRendered = useCallback(
    ({
      overscanStartIndex,
      overscanStopIndex,
    }: {
      overscanStartIndex: number;
      overscanStopIndex: number;
    }) => {
      for (let i = overscanStartIndex; i <= overscanStopIndex; i++) {
        requestPageDimension(i + 1);
      }
      if (initialScrollIndex !== undefined) setInitialScrollIndex(undefined);
    },
    [requestPageDimension, initialScrollIndex],
  );

  const rowRenderer: ListRowRenderer = ({ index, key, style }) => {
    const page = index + 1;
    const ratio = getRatio(index);
    const thumbnailSkeleton = (
      <div
        className="pdf-preview__thumbnail-skeleton"
        style={{ width: THUMBNAIL_WIDTH, height: THUMBNAIL_WIDTH * ratio }}
      />
    );
    return (
      <div
        key={key}
        style={{
          ...style,
          paddingTop: THUMBNAIL_GAP,
          paddingBottom: index === numPages - 1 ? THUMBNAIL_GAP : 0,
          boxSizing: "border-box",
        }}
      >
        <button
          data-thumb-page={page}
          className={`pdf-preview__thumbnail${currentPage === page ? " pdf-preview__thumbnail--active" : ""}`}
          onClick={() => {
            isClickNavRef.current = true;
            goToPage(page);
          }}
          aria-label={`Go to page ${page}`}
        >
          <Thumbnail
            pageNumber={page}
            width={THUMBNAIL_WIDTH}
            loading={thumbnailSkeleton}
          />
          <span className="pdf-preview__thumbnail-number">{page}</span>
        </button>
      </div>
    );
  };

  return (
    <div
      className={`pdf-preview__sidebar${!isOpen ? " pdf-preview__sidebar--closed" : ""}`}
    >
      <AutoSizer>
        {({ height, width }) => (
          <List
            ref={listRef}
            height={height}
            width={width}
            rowCount={numPages}
            rowHeight={rowHeight}
            estimatedRowSize={
              THUMBNAIL_WIDTH * FALLBACK_RATIO +
              THUMBNAIL_LABEL_SPACE +
              THUMBNAIL_GAP
            }
            overscanRowCount={5}
            rowRenderer={rowRenderer}
            scrollToIndex={initialScrollIndex}
            scrollToAlignment="center"
            onRowsRendered={handleRowsRendered}
            style={{ outline: "none" }}
          />
        )}
      </AutoSizer>
    </div>
  );
}
