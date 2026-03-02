import { useEffect, useRef, useState } from "react";
import { Document, Thumbnail } from "react-pdf";
import { useVirtualizer } from "@tanstack/react-virtual";

const options = {
  cMapUrl: "/cmaps/",
  standardFontDataUrl: "/standard_fonts/",
  wasmUrl: "/wasm/",
  isEvalSupported: false,
};

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
  const sidebarRef = useRef<HTMLDivElement>(null);
  const [isDocLoaded, setIsDocLoaded] = useState(false);

  const virtualizer = useVirtualizer({
    count: numPages,
    getScrollElement: () => sidebarRef.current,
    estimateSize: () => THUMBNAIL_HEIGHT,
    gap: THUMBNAIL_GAP,
    overscan: 5,
  });

  // Auto-scroll active thumbnail into view
  useEffect(() => {
    if (!isDocLoaded) return;
    virtualizer.scrollToIndex(currentPage - 1, { align: "center" });
  }, [isDocLoaded, currentPage, virtualizer]);

  if (!file) {
    return (
      <div
        className={`pdf-preview__sidebar${!isOpen ? " pdf-preview__sidebar--closed" : ""}`}
        ref={sidebarRef}
      >
        <div className="pdf-preview__thumbnail-skeleton" />
      </div>
    );
  }

  return (
    <div
      className={`pdf-preview__sidebar${!isOpen ? " pdf-preview__sidebar--closed" : ""}`}
      ref={sidebarRef}
    >
      <Document
        file={file}
        options={options}
        loading={<div className="pdf-preview__thumbnail-skeleton" />}
        onLoadSuccess={() => setIsDocLoaded(true)}
        // Thumbnails may contain clickable internal links (e.g., table of contents).
        // Without onItemClick, react-pdf cannot resolve those links since only
        // thumbnails are rendered here, not full pages. We intercept the click
        // and navigate the main viewer instead.
        // onItemClick={({ pageNumber }) => goToPage(pageNumber)}
      >
        <div
          style={{
            width: "116px", // Needed to be able to center the layout of the thumbnails.
            height: virtualizer.getTotalSize(),
            position: "relative",
          }}
        >
          {virtualizer.getVirtualItems().map((virtualItem) => {
            const page = virtualItem.index + 1;
            return (
              <button
                key={virtualItem.index}
                data-thumb-page={page}
                style={{
                  position: "absolute",
                  top: virtualItem.start,
                  height: THUMBNAIL_HEIGHT,
                }}
                className={`pdf-preview__thumbnail${currentPage === page ? " pdf-preview__thumbnail--active" : ""}`}
                onClick={() => goToPage(page)}
                aria-label={`Go to page ${page}`}
              >
                <Thumbnail
                  pageNumber={page}
                  width={105}
                  loading={<div className="pdf-preview__thumbnail-skeleton" />}
                />
                <span className="pdf-preview__thumbnail-number">{page}</span>
              </button>
            );
          })}
        </div>
      </Document>
    </div>
  );
}
