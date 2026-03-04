import { useEffect, useRef, useState } from "react";
import { Document, Thumbnail } from "react-pdf";
import { AutoSizer, List } from "react-virtualized";
import type { ListRowRenderer } from "react-virtualized";
import { pdfOptions } from "./pdfOptions";

interface PdfThumbnailSidebarProps {
  file?: File | null;
  numPages: number;
  currentPage: number;
  goToPage: (page: number) => void;
  isOpen: boolean;
}

const TRANSITION_DELAY = 300;
const THUMBNAIL_HEIGHT = 178;
const THUMBNAIL_GAP = 12;
const ROW_HEIGHT = THUMBNAIL_HEIGHT + THUMBNAIL_GAP;

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
    if (props.isOpen) {
      setUnmount(false);
      setTimeout(() => setIsOpenProxy(true), 100);
    } else {
      setIsOpenProxy(false);
      // The 1.1 is to allow for the transition to finish.
      // It is a safety margin to avoid the component being unmounted too early.
      setTimeout(() => setUnmount(true), TRANSITION_DELAY * 1.1);
    }
  }, [props.isOpen]);

  if (unmount) {
    return null;
  }

  return <PdfThumbnailSidebarContent {...props} isOpen={isOpenProxy} />;
}

export function PdfThumbnailSidebarContent({
  file,
  numPages,
  currentPage,
  goToPage,
  isOpen,
}: PdfThumbnailSidebarProps) {
  const listRef = useRef<List>(null);
  const [isDocLoaded, setIsDocLoaded] = useState(false);

  // Auto-scroll active thumbnail into view
  useEffect(() => {
    if (!isDocLoaded || !listRef.current) return;
    listRef.current.scrollToRow(currentPage - 1);
  }, [isDocLoaded, currentPage]);

  const thumbnailSkeleton = <div className="pdf-preview__thumbnail-skeleton" />;

  const rowRenderer: ListRowRenderer = ({ index, key, style }) => {
    const page = index + 1;
    return (
      <div
        key={key}
        style={{
          ...style,
          paddingBottom: index < numPages - 1 ? THUMBNAIL_GAP : 0,
          boxSizing: "border-box",
        }}
      >
        <button
          data-thumb-page={page}
          className={`pdf-preview__thumbnail${currentPage === page ? " pdf-preview__thumbnail--active" : ""}`}
          onClick={() => goToPage(page)}
          aria-label={`Go to page ${page}`}
        >
          <Thumbnail
            pageNumber={page}
            width={105}
            loading={thumbnailSkeleton}
          />
          <span className="pdf-preview__thumbnail-number">{page}</span>
        </button>
      </div>
    );
  };

  const loadingContainerSkeleton = (
    <div className="pdf-preview__sidebar-skeleton">{thumbnailSkeleton}</div>
  );

  return (
    <div
      className={`pdf-preview__sidebar${!isOpen ? " pdf-preview__sidebar--closed" : ""}`}
    >
      {file ? (
        <Document
          file={file}
          options={pdfOptions}
          loading={loadingContainerSkeleton}
          onLoadSuccess={() => setIsDocLoaded(true)}
        >
          <AutoSizer>
            {({ height, width }) => (
              <List
                ref={listRef}
                height={height}
                width={width}
                rowCount={numPages}
                rowHeight={ROW_HEIGHT}
                overscanRowCount={5}
                rowRenderer={rowRenderer}
                scrollToAlignment="center"
                style={{ outline: "none" }}
              />
            )}
          </AutoSizer>
        </Document>
      ) : (
        loadingContainerSkeleton
      )}
    </div>
  );
}
