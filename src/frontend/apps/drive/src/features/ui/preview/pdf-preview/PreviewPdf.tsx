import { useCallback, useEffect, useRef, useState } from "react";
import { Document, Page, pdfjs } from "react-pdf";
import { useModals } from "@gouvfr-lasuite/cunningham-react";
import { useTranslation } from "react-i18next";
import "react-pdf/dist/Page/AnnotationLayer.css";
import "react-pdf/dist/Page/TextLayer.css";

import { useDebouncedResize } from "./useDebouncedResize";
import { usePdfNavigation } from "./usePdfNavigation";
import { PdfThumbnailSidebar } from "./PdfThumbnailSidebar";
import { PdfControls } from "./PdfControls";

pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;

const options = {
  cMapUrl: "/cmaps/",
  standardFontDataUrl: "/standard_fonts/",
  wasmUrl: "/wasm/",
  isEvalSupported: false,
};

const BASE_WIDTH = 800;
const PRELOAD_PAGES = 4;

export function PreviewPdf({ src }: { src: string }) {
  const [file, setFile] = useState<File | null>(null);
  const [numPages, setNumPages] = useState<number>(1);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const sidebarRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const visiblePages = useRef(new Set<number>());
  const visibleThumbnails = useRef(new Set<number>());
  const [, setRenderTick] = useState(0);
  const modals = useModals();
  const { t } = useTranslation();
  const size = useDebouncedResize();

  const {
    currentPage,
    setCurrentPage,
    pageInputValue,
    setPageInputValue,
    isScrollingToPage,
    goToPreviousPage,
    goToNextPage,
    goToPage,
    onDocumentLoadSuccess: onNavLoadSuccess,
    handlePageInputChange,
    handlePageInputSubmit,
    handlePageInputKeyDown,
  } = usePdfNavigation({ numPages, containerRef });

  const getWidth = () => {
    if (size.width < BASE_WIDTH) {
      return size.width;
    }
    return BASE_WIDTH;
  };

  const [width, setWidth] = useState(getWidth());
  useEffect(() => {
    setWidth(getWidth());
  }, [size.width]);

  const pageHeight = width * 1.414;

  useEffect(() => {
    const fetchPdf = async () => {
      setIsLoading(true);
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
      } finally {
        setIsLoading(false);
      }
    };

    fetchPdf();
  }, [src]);

  function onDocumentLoadSuccess(pdf: Parameters<typeof onNavLoadSuccess>[0]) {
    const nextNumPages = onNavLoadSuccess(pdf);
    setNumPages(nextNumPages);
  }

  // Virtualization observer: track which pages are near the viewport
  useEffect(() => {
    const container = containerRef.current;
    if (!container || numPages <= 0) return;

    const observer = new IntersectionObserver(
      (entries) => {
        let changed = false;
        for (const entry of entries) {
          const pageNum = Number(
            (entry.target as HTMLElement).dataset.pageNumber,
          );
          if (entry.isIntersecting) {
            if (!visiblePages.current.has(pageNum)) {
              visiblePages.current.add(pageNum);
              changed = true;
            }
          } else {
            if (visiblePages.current.has(pageNum)) {
              visiblePages.current.delete(pageNum);
              changed = true;
            }
          }
        }
        if (changed) {
          setRenderTick((t) => t + 1);
        }
      },
      { root: container, rootMargin: `${PRELOAD_PAGES * pageHeight}px` },
    );

    const wrappers = container.querySelectorAll("[data-page-number]");
    wrappers.forEach((el) => observer.observe(el));

    return () => observer.disconnect();
  }, [numPages, width, pageHeight]);

  // Current page tracking observer
  useEffect(() => {
    const container = containerRef.current;
    if (!container || numPages <= 0) return;

    const observer = new IntersectionObserver(
      (entries) => {
        if (isScrollingToPage.current) return;
        for (const entry of entries) {
          if (entry.isIntersecting) {
            const pageNum = Number(
              (entry.target as HTMLElement).dataset.pageNumber,
            );
            setCurrentPage(pageNum);
            setPageInputValue(String(pageNum));
          }
        }
      },
      { root: container, threshold: 0.5 },
    );

    const wrappers = container.querySelectorAll("[data-page-number]");
    wrappers.forEach((el) => observer.observe(el));

    return () => observer.disconnect();
  }, [numPages, width, isScrollingToPage, setCurrentPage, setPageInputValue]);

  // Thumbnail virtualization observer
  useEffect(() => {
    const sidebar = sidebarRef.current;
    if (!sidebar || !isSidebarOpen || numPages <= 0) return;

    const observer = new IntersectionObserver(
      (entries) => {
        let changed = false;
        for (const entry of entries) {
          const pageNum = Number(
            (entry.target as HTMLElement).dataset.thumbPage,
          );
          if (entry.isIntersecting) {
            if (!visibleThumbnails.current.has(pageNum)) {
              visibleThumbnails.current.add(pageNum);
              changed = true;
            }
          } else {
            if (visibleThumbnails.current.has(pageNum)) {
              visibleThumbnails.current.delete(pageNum);
              changed = true;
            }
          }
        }
        if (changed) {
          setRenderTick((t) => t + 1);
        }
      },
      { root: sidebar, rootMargin: "200%" },
    );

    const thumbs = sidebar.querySelectorAll("[data-thumb-page]");
    thumbs.forEach((el) => observer.observe(el));

    return () => observer.disconnect();
  }, [numPages, isSidebarOpen]);

  useEffect(() => {
    if (!isSidebarOpen || !sidebarRef.current) return;
    const active = sidebarRef.current.querySelector(
      ".pdf-preview__thumbnail--active",
    );
    if (active) {
      active.scrollIntoView({ block: "nearest", behavior: "smooth" });
    }
  }, [currentPage, isSidebarOpen]);

  const handlePdfClick = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      const target = e.target as HTMLElement;
      const anchor = target.closest("a");

      if (anchor && anchor.href) {
        e.preventDefault();
        e.stopPropagation();

        modals.confirmationModal({
          title: t("file_preview.external_link.title"),
          children: (
            <div>
              <p>{t("file_preview.external_link.description")}</p>
              <pre className="pdf-preview__external-link">{anchor.href}</pre>
              <p>{t("file_preview.external_link.confirm_question")}</p>
            </div>
          ),
          onDecide: (decision) => {
            if (decision === "yes") {
              window.open(anchor.href, "_blank", "noopener,noreferrer");
            }
          },
        });
      }
    },
    [modals, t],
  );

  if (isLoading) {
    return (
      <div className="pdf-preview">
        <div className="pdf-preview__loading">
          <div className="pdf-preview__spinner"></div>
          <span>Loading PDF...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="pdf-preview">
        <div className="pdf-preview__error">Error: {error}</div>
      </div>
    );
  }

  if (!file) {
    return null;
  }

  return (
    <div className="pdf-preview">
      <div className="pdf-preview__body">
        {isSidebarOpen && (
          <PdfThumbnailSidebar
            file={file}
            numPages={numPages}
            currentPage={currentPage}
            visibleThumbnails={visibleThumbnails.current}
            goToPage={goToPage}
            sidebarRef={sidebarRef}
          />
        )}
        <div className="pdf-preview__container" ref={containerRef}>
          <div className="pdf-preview__page-wrapper" onClick={handlePdfClick}>
            <Document
              file={file}
              onLoadSuccess={onDocumentLoadSuccess}
              options={options}
            >
              {Array.from({ length: numPages }, (_, i) => {
                const page = i + 1;
                const isVisible = visiblePages.current.has(page);
                return (
                  <div
                    key={page}
                    data-page-number={page}
                    style={{ minHeight: pageHeight, width }}
                  >
                    {isVisible && <Page pageNumber={page} width={width} />}
                  </div>
                );
              })}
            </Document>
          </div>
        </div>
      </div>
      <PdfControls
        currentPage={currentPage}
        numPages={numPages}
        pageInputValue={pageInputValue}
        isSidebarOpen={isSidebarOpen}
        onToggleSidebar={() => setIsSidebarOpen((prev) => !prev)}
        onGoToPreviousPage={goToPreviousPage}
        onGoToNextPage={goToNextPage}
        onPageInputChange={handlePageInputChange}
        onPageInputSubmit={handlePageInputSubmit}
        onPageInputKeyDown={handlePageInputKeyDown}
      />
    </div>
  );
}
