import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { pdfjs } from "react-pdf";
import "react-pdf/dist/Page/AnnotationLayer.css";
import "react-pdf/dist/Page/TextLayer.css";
import { useVirtualizer } from "@tanstack/react-virtual";

import { useDebouncedResize } from "./useDebouncedResize";
import { usePdfNavigation } from "./usePdfNavigation";
import { PdfThumbnailSidebar } from "./PdfThumbnailSidebar";
import { PdfControls } from "./PdfControls";
import { PdfPageViewer } from "./PdfPageViewer";
import { useRedirectDisclaimer } from "./useRedirectDisclaimer";

pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;

const BASE_WIDTH = 800;
const PAGE_MARGIN = 32;
const PAGE_GAP = 16;

export function PreviewPdf({ src }: { src: string }) {
  const [file, setFile] = useState<File | null>(null);
  const [numPages, setNumPages] = useState<number>(1);
  const [error, setError] = useState<string | null>(null);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const { handlePdfClick } = useRedirectDisclaimer();
  const size = useDebouncedResize();

  const getWidth = () => {
    if (BASE_WIDTH + PAGE_MARGIN > size.width) {
      return size.width - PAGE_MARGIN;
    }
    return BASE_WIDTH;
  };

  const [width, setWidth] = useState(getWidth());
  useEffect(() => {
    setWidth(getWidth());
  }, [size.width]);

  const [zoom, setZoom] = useState(1);

  const zoomIn = () => {
    setZoom((prev) => Math.min(3, prev + 0.25));
  };
  const zoomOut = () => {
    setZoom((prev) => Math.max(0.5, prev - 0.25));
  };
  const zoomReset = () => {
    setZoom(1);
  };

  const pageHeight = width * 1.414;

  const virtualizer = useVirtualizer({
    count: numPages,
    getScrollElement: () => containerRef.current,
    estimateSize: () => pageHeight * zoom,
    gap: PAGE_GAP,
    overscan: 3,
  });

  // Derive current page from the virtualizer's scroll offset
  const currentPage = useMemo(() => {
    const items = virtualizer.getVirtualItems();
    if (items.length === 0) return 1;

    const scrollElement = containerRef.current;
    if (!scrollElement) return 1;

    const scrollOffset = virtualizer.scrollOffset ?? 0;
    const viewportCenter = scrollOffset + scrollElement.clientHeight / 2;

    // Find the page whose range contains the viewport center
    for (const item of items) {
      const itemEnd = item.start + item.size;
      if (viewportCenter >= item.start && viewportCenter < itemEnd) {
        return item.index + 1;
      }
    }

    // Fallback: first visible item
    return items[0].index + 1;
  }, [virtualizer.getVirtualItems(), virtualizer.scrollOffset]);

  const scrollToPage = useCallback(
    (page: number) => {
      virtualizer.scrollToIndex(page - 1, { align: "start" });
    },
    [virtualizer],
  );

  const {
    goToPreviousPage,
    goToNextPage,
    goToPage,
    onDocumentLoadSuccess: onNavLoadSuccess,
    pageInputValue,
    setPageInputValue,
    handlePageInputChange,
    handlePageInputSubmit,
    handlePageInputKeyDown,
  } = usePdfNavigation({ numPages, currentPage, scrollToPage });

  // Sync page input value when currentPage changes from scrolling
  useEffect(() => {
    setPageInputValue(String(currentPage));
  }, [currentPage, setPageInputValue]);

  useEffect(() => {
    const fetchPdf = async () => {
      setError(null);

      try {
        const response = await fetch(src, { credentials: "include" });

        if (!response.ok) {
          throw new Error(`Failed to fetch PDF: ${response.status}`);
        }

        const blob = await response.blob();
        const filename = src.split("/").pop() || "document.pdf";
        const pdfFile = new File([blob], filename, { type: "application/pdf" });

        setFile(pdfFile);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load PDF");
      }
    };

    fetchPdf();
  }, [src]);

  function onDocumentLoadSuccess(pdf: Parameters<typeof onNavLoadSuccess>[0]) {
    const nextNumPages = onNavLoadSuccess(pdf);
    setNumPages(nextNumPages);
  }

  if (error) {
    return (
      <div className="pdf-preview">
        <div className="pdf-preview__error">Error: {error}</div>
      </div>
    );
  }

  return (
    <div className="pdf-preview">
      <div className="pdf-preview__body">
        <PdfThumbnailSidebar
          file={file}
          numPages={numPages}
          currentPage={currentPage}
          goToPage={goToPage}
          isOpen={isSidebarOpen}
        />
        <PdfPageViewer
          file={file}
          width={width}
          pageHeight={pageHeight}
          zoom={zoom}
          containerRef={containerRef}
          totalSize={virtualizer.getTotalSize()}
          virtualItems={virtualizer.getVirtualItems()}
          onDocumentLoadSuccess={onDocumentLoadSuccess}
          onClick={handlePdfClick}
        />
      </div>
      <PdfControls
        currentPage={currentPage}
        numPages={numPages}
        pageInputValue={pageInputValue}
        isSidebarOpen={isSidebarOpen}
        zoom={zoom}
        onToggleSidebar={() => setIsSidebarOpen((prev) => !prev)}
        onGoToPreviousPage={goToPreviousPage}
        onGoToNextPage={goToNextPage}
        onPageInputChange={handlePageInputChange}
        onPageInputSubmit={handlePageInputSubmit}
        onPageInputKeyDown={handlePageInputKeyDown}
        onZoomIn={zoomIn}
        onZoomReset={zoomReset}
        onZoomOut={zoomOut}
      />
    </div>
  );
}
