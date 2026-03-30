import "./pdfPolyfills";
import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { useQuery } from "@tanstack/react-query";
import { Document, pdfjs } from "react-pdf";
import "react-pdf/dist/Page/AnnotationLayer.css";
import "react-pdf/dist/Page/TextLayer.css";
import "react-virtualized/styles.css";
import { Icon, IconType } from "@gouvfr-lasuite/ui-kit";

import { usePdfNavigation } from "./usePdfNavigation";
import { PdfThumbnailSidebar } from "./PdfThumbnailSidebar";
import { PdfControls } from "./PdfControls";
import { PdfPageViewer } from "./PdfPageViewer";
import type { PdfPageViewerHandle } from "./PdfPageViewer";
import { useRedirectDisclaimer } from "./useRedirectDisclaimer";
import { OutdatedBrowserPreview } from "./OutdatedBrowserPreview";
import { pdfOptions } from "./pdfOptions";

// Configure PDF.js worker source for PDF loading
pdfjs.GlobalWorkerOptions.workerSrc = "/pdf.worker.mjs";

export function PreviewPdf({ src }: { src: string }) {
  const { t } = useTranslation();
  const [numPages, setNumPages] = useState<number>(1);
  const [documentError, setDocumentError] = useState<
    "generic" | "outdated" | null
  >(null);
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
    onItemClick,
  } = usePdfNavigation({ numPages, currentPage, scrollToPage });

  // Sync page input value when currentPage changes from scrolling
  useEffect(() => {
    setPageInputValue(String(currentPage));
  }, [currentPage, setPageInputValue]);

  const { data: file, error } = useQuery<File, Error>({
    queryKey: ["pdf", src],
    queryFn: async ({ signal }) => {
      const response = await fetch(src, {
        credentials: "include",
        signal,
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch PDF: ${response.status}`);
      }

      const blob = await response.blob();
      const filename = src.split("/").pop() || "document.pdf";
      return new File([blob], filename, { type: "application/pdf" });
    },
    staleTime: Infinity,
  });

  const onDocumentLoadSuccess = useCallback(
    (pdf: Parameters<typeof onNavLoadSuccess>[0]) => {
      const nextNumPages = onNavLoadSuccess(pdf);
      setNumPages(nextNumPages);
    },
    [onNavLoadSuccess],
  );

  const handleDocumentError = useCallback((error: Error) => {
    const pdfErrors = [
      "InvalidPDFException",
      "FormatError",
      "PasswordException",
      "ResponseException",
    ];
    setDocumentError(pdfErrors.includes(error.name) ? "generic" : "outdated");
  }, []);

  if (error?.message || documentError === "generic") {
    return (
      <div className="file-preview-unsupported">
        <div className="file-preview-unsupported__icon">
          <Icon name="error" type={IconType.OUTLINED} size={48} />
        </div>
        <p className="file-preview-unsupported__title">
          {t("file_preview.error.title")}
        </p>
        <p className="file-preview-unsupported__description">
          {t("file_preview.error.description")}
        </p>
      </div>
    );
  }

  if (documentError === "outdated") {
    return <OutdatedBrowserPreview />;
  }

  const loadingSkeleton = (
    <div className="pdf-preview__container-skeleton">
      <div className="pdf-preview__page-skeleton" />
    </div>
  );

  return (
    <div className="pdf-preview">
      <div className="pdf-preview__body">
        {file ? (
          <Document
            file={file}
            onLoadSuccess={onDocumentLoadSuccess}
            onItemClick={onItemClick}
            options={pdfOptions}
            loading={loadingSkeleton}
            onLoadError={handleDocumentError}
          >
            <PdfThumbnailSidebar
              numPages={numPages}
              currentPage={currentPage}
              goToPage={goToPage}
              isOpen={isSidebarOpen}
            />
            <PdfPageViewer
              ref={viewerRef}
              numPages={numPages}
              zoom={zoom}
              onCurrentPageChange={setCurrentPage}
              onClick={handlePdfClick}
            />
          </Document>
        ) : (
          loadingSkeleton
        )}
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
