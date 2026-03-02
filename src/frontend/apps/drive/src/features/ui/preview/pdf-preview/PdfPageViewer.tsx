import {
  forwardRef,
  useCallback,
  useEffect,
  useImperativeHandle,
  useMemo,
  useRef,
} from "react";
import { Document, Page } from "react-pdf";
import type { PDFDocumentProxy } from "pdfjs-dist";
import { useVirtualizer } from "@tanstack/react-virtual";

const options = {
  cMapUrl: "/cmaps/",
  standardFontDataUrl: "/standard_fonts/",
  wasmUrl: "/wasm/",
  isEvalSupported: false,
};

const PAGE_GAP = 16;

export interface PdfPageViewerHandle {
  scrollToPage: (page: number) => void;
}

interface PdfPageViewerProps {
  file?: File | null;
  numPages: number;
  width: number;
  pageHeight: number;
  zoom: number;
  onDocumentLoadSuccess: (pdf: PDFDocumentProxy) => void;
  onCurrentPageChange: (page: number) => void;
  onClick: (e: React.MouseEvent<HTMLDivElement>) => void;
}

export const PdfPageViewer = forwardRef<
  PdfPageViewerHandle,
  PdfPageViewerProps
>(function PdfPageViewer(
  {
    file,
    numPages,
    width,
    pageHeight,
    zoom,
    onDocumentLoadSuccess,
    onCurrentPageChange,
    onClick,
  },
  ref,
) {
  const containerRef = useRef<HTMLDivElement>(null);

  // When scrollToPage is called, the virtualizer scrolls to the target page
  // but currentPage (computed from viewport center) may briefly land on an
  // adjacent page, triggering a parent re-render that shifts scroll again,
  // causing an infinite loop. These refs lock the reported page to the
  // scroll target for 150ms while the virtualizer settles.
  const programmaticPageRef = useRef<number | null>(null);
  const programmaticTimerRef = useRef<ReturnType<typeof setTimeout>>();

  useEffect(() => {
    return () => clearTimeout(programmaticTimerRef.current);
  }, []);

  const virtualizer = useVirtualizer({
    count: numPages,
    getScrollElement: () => containerRef.current,
    estimateSize: () => pageHeight * zoom,
    gap: PAGE_GAP * zoom,
    overscan: 3,
    // Stolen from https://github.com/TanStack/virtual/issues/659#issuecomment-2915244925
    // Thank you <3
    measureElement: (element, _entry, instance) => {
      const direction = instance.scrollDirection;
      if (direction === "forward" || direction === null) {
        // Allow remeasuring when scrolling down or direction is null
        return element.getBoundingClientRect().height;
      } else {
        // When scrolling up, use cached measurement to prevent stuttering
        const indexKey = Number(element.getAttribute("data-index"));
        const cachedMeasurement = instance.measurementsCache[indexKey]?.size;
        return cachedMeasurement || element.getBoundingClientRect().height;
      }
    },
  });

  const currentPage = useMemo(() => {
    const items = virtualizer.getVirtualItems();
    if (items.length === 0) return 1;

    const scrollElement = containerRef.current;
    if (!scrollElement) return 1;

    const scrollOffset = virtualizer.scrollOffset ?? 0;
    const viewportCenter = scrollOffset + scrollElement.clientHeight / 2;
    console.log("scrollOffset", scrollOffset, "viewportCenter", viewportCenter);

    for (const item of items) {
      const itemEnd = item.start + item.size;
      if (item.start <= viewportCenter && viewportCenter < itemEnd) {
        return item.index + 1;
      }
    }

    return items[0].index + 1;
  }, [virtualizer.getVirtualItems(), virtualizer.scrollOffset]);
  console.log("currentPage", currentPage);

  useEffect(() => {
    console.log(
      "useEffect",
      programmaticPageRef.current,
      currentPage,
      programmaticPageRef.current ?? currentPage,
    );
    onCurrentPageChange(programmaticPageRef.current ?? currentPage);
  }, [currentPage]);

  const scrollToPage = useCallback(
    (page: number) => {
      clearTimeout(programmaticTimerRef.current);
      programmaticPageRef.current = page;
      programmaticTimerRef.current = setTimeout(() => {
        programmaticPageRef.current = null;
      }, 150);
      console.log("scrollToPage", page);
      virtualizer.scrollToIndex(page - 1, { align: "start" });
    },
    [virtualizer],
  );

  useImperativeHandle(ref, () => ({ scrollToPage }), [scrollToPage]);

  const pageSkeleton = (
    <div
      className="pdf-preview__page-skeleton"
      style={{ height: pageHeight * zoom, width: width * zoom }}
    />
  );

  if (!file) {
    return (
      <div className="pdf-preview__container" ref={containerRef}>
        <div className="pdf-preview__page-wrapper">{pageSkeleton}</div>
      </div>
    );
  }

  return (
    <div className="pdf-preview__container" ref={containerRef}>
      <div className="pdf-preview__page-wrapper" onClick={onClick}>
        <Document
          file={file}
          onLoadSuccess={onDocumentLoadSuccess}
          options={options}
          loading={pageSkeleton}
        >
          <div
            style={{
              width: width * zoom,
              height: virtualizer.getTotalSize(),
              position: "relative",
            }}
          >
            {virtualizer.getVirtualItems().map((virtualItem) => (
              <div
                key={virtualItem.index}
                data-index={virtualItem.index}
                data-page-number={virtualItem.index + 1}
                ref={virtualizer.measureElement}
                style={{
                  position: "absolute",
                  top: virtualItem.start,
                  width: width * zoom,
                }}
              >
                <Page
                  pageNumber={virtualItem.index + 1}
                  width={width}
                  scale={zoom}
                  loading={pageSkeleton}
                />
              </div>
            ))}
          </div>
        </Document>
      </div>
    </div>
  );
});
