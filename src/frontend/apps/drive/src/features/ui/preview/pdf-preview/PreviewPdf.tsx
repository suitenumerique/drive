import { useCallback, useEffect, useRef, useState } from "react";
import { pdfjs } from "react-pdf";
import "react-pdf/dist/Page/AnnotationLayer.css";
import "react-pdf/dist/Page/TextLayer.css";
import "react-virtualized/styles.css";

import { usePdfNavigation } from "./usePdfNavigation";
import { PdfThumbnailSidebar } from "./PdfThumbnailSidebar";
import { PdfControls } from "./PdfControls";
import { PdfPageViewer } from "./PdfPageViewer";
import type { PdfPageViewerHandle } from "./PdfPageViewer";
import { useRedirectDisclaimer } from "./useRedirectDisclaimer";

pdfjs.GlobalWorkerOptions.workerSrc = "/pdf.worker.mjs";

export function PreviewPdf({ src }: { src: string }) {
  const [file, setFile] = useState<File | null>(null);
  const [numPages, setNumPages] = useState<number>(1);
  const [error, setError] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const viewerRef = useRef<PdfPageViewerHandle>(null);
  const { handlePdfClick } = useRedirectDisclaimer();

  const [zoom, setZoom] = useState(1);

  const zoomIn = useCallback(() => {
    setZoom((prev) => Math.min(3, prev + 0.25));
  }, []);
  const zoomOut = useCallback(() => {
    setZoom((prev) => Math.max(0.5, prev - 0.25));
  }, []);
  const zoomReset = useCallback(() => {
    setZoom(1);
  }, []);
  const toggleSidebar = useCallback(() => {
    setIsSidebarOpen((prev) => !prev);
  }, []);

  const scrollToPage = useCallback((page: number) => {
    viewerRef.current?.scrollToPage(page);
  }, []);

  const {
    goToPage,
    onDocumentLoadSuccess: onNavLoadSuccess,
    pageInputValue,
    setPageInputValue,
    handlePageInputChange,
    handlePageInputSubmit,
    handlePageInputKeyDown,
  } = usePdfNavigation({ numPages, currentPage, scrollToPage });

  // onItemClick handles internal PDF links (e.g. table of contents entries).
  // It is called by react-pdf's Document via a viewer ref that is created once
  // with useRef, so the callback is captured in a stale closure from the first
  // render. We use a ref to always access the latest goToPage (which depends
  // on numPages) so navigation targets the correct page.
  //
  // onClick (handlePdfClick) handles regular DOM clicks on the annotation layer
  // — it intercepts external links to show a redirect disclaimer modal.
  const goToPageRef = useRef(goToPage);
  useEffect(() => {
    goToPageRef.current = goToPage;
  }, [goToPage]);

  const onItemClick = useCallback((args: { pageNumber: number }) => {
    goToPageRef.current(args.pageNumber);
  }, []);

  // Sync page input value when currentPage changes from scrolling
  useEffect(() => {
    setPageInputValue(String(currentPage));
  }, [currentPage, setPageInputValue]);

  useEffect(() => {
    const controller = new AbortController();

    const fetchPdf = async () => {
      setError(null);

      try {
        const response = await fetch(src, {
          credentials: "include",
          signal: controller.signal,
        });

        if (!response.ok) {
          throw new Error(`Failed to fetch PDF: ${response.status}`);
        }

        const blob = await response.blob();
        const filename = src.split("/").pop() || "document.pdf";
        const pdfFile = new File([blob], filename, { type: "application/pdf" });

        setFile(pdfFile);
      } catch (err) {
        if (err instanceof DOMException && err.name === "AbortError") return;
        setError(err instanceof Error ? err.message : "Failed to load PDF");
      }
    };

    fetchPdf();
    return () => controller.abort();
  }, [src]);

  const onDocumentLoadSuccess = useCallback(
    (pdf: Parameters<typeof onNavLoadSuccess>[0]) => {
      const nextNumPages = onNavLoadSuccess(pdf);
      setNumPages(nextNumPages);
    },
    [onNavLoadSuccess],
  );

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
          ref={viewerRef}
          file={file}
          numPages={numPages}
          zoom={zoom}
          onDocumentLoadSuccess={onDocumentLoadSuccess}
          onCurrentPageChange={setCurrentPage}
          onClick={handlePdfClick}
          onItemClick={onItemClick}
        />
      </div>
      <PdfControls
        numPages={numPages}
        pageInputValue={pageInputValue}
        isSidebarOpen={isSidebarOpen}
        onToggleSidebar={toggleSidebar}
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
