import { forwardRef, useCallback, useEffect, useImperativeHandle, useMemo, useRef } from "react";
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

export const PdfPageViewer = forwardRef<PdfPageViewerHandle, PdfPageViewerProps>(
  function PdfPageViewer(
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

    const virtualizer = useVirtualizer({
      count: numPages,
      getScrollElement: () => containerRef.current,
      estimateSize: () => pageHeight * zoom,
      gap: PAGE_GAP,
      overscan: 3,
    });

    const currentPage = useMemo(() => {
      const items = virtualizer.getVirtualItems();
      if (items.length === 0) return 1;

      const scrollElement = containerRef.current;
      if (!scrollElement) return 1;

      const scrollOffset = virtualizer.scrollOffset ?? 0;
      const viewportCenter = scrollOffset + scrollElement.clientHeight / 2;

      for (const item of items) {
        const itemEnd = item.start + item.size;
        if (viewportCenter >= item.start && viewportCenter < itemEnd) {
          return item.index + 1;
        }
      }

      return items[0].index + 1;
    }, [virtualizer.getVirtualItems(), virtualizer.scrollOffset]);

    useEffect(() => {
      onCurrentPageChange(currentPage);
    }, [currentPage]);

    const scrollToPage = useCallback(
      (page: number) => {
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
            <div style={{ width: width * zoom, height: virtualizer.getTotalSize(), position: "relative" }}>
              {virtualizer.getVirtualItems().map((virtualItem) => (
                <div
                  key={virtualItem.index}
                  data-page-number={virtualItem.index + 1}
                  style={{
                    position: "absolute",
                    top: virtualItem.start,
                    height: pageHeight * zoom,
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
  },
);
