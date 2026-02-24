import { useCallback, useEffect, useRef, useState } from "react";
import { Document, Page, Thumbnail, pdfjs } from "react-pdf";
import type { PDFDocumentProxy } from "pdfjs-dist";
import { Button, useModals } from "@gouvfr-lasuite/cunningham-react";
import { Icon } from "@gouvfr-lasuite/ui-kit";
import { useTranslation } from "react-i18next";
import "react-pdf/dist/Page/AnnotationLayer.css";
import "react-pdf/dist/Page/TextLayer.css";

pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;

const options = {
  cMapUrl: "/cmaps/",
  standardFontDataUrl: "/standard_fonts/",
  wasmUrl: "/wasm/",
  isEvalSupported: false,
};

const BASE_WIDTH = 800;

function debounce<T extends (...args: any[]) => any>(
  func: T,
  timeout = 300,
): ((...args: Parameters<T>) => void) & { cancel: () => void } {
  let timer: ReturnType<typeof setTimeout> | undefined;
  const debouncedFunc = (...args: Parameters<T>) => {
    if (timer !== undefined) {
      clearTimeout(timer);
    }
    timer = setTimeout(() => {
      func(...args);
    }, timeout);
  };
  debouncedFunc.cancel = () => {
    if (timer !== undefined) {
      clearTimeout(timer);
    }
  };
  return debouncedFunc;
}

const useDebouncedResize = () => {
  const [size, setSize] = useState({
    width: window.innerWidth,
    height: window.innerHeight,
  });

  useEffect(() => {
    const handleResize = debounce(() => {
      setSize({ width: window.innerWidth, height: window.innerHeight });
    }, 100);
    window.addEventListener("resize", handleResize);
    return () => {
      handleResize.cancel();
      window.removeEventListener("resize", handleResize);
    };
  }, []);

  return size;
};

export function PreviewPdf({ src }: { src: string }) {
  const [file, setFile] = useState<File | null>(null);
  const [numPages, setNumPages] = useState<number>(1);
  const [currentPage, setCurrentPage] = useState<number>(1);

  const [pageInputValue, setPageInputValue] = useState<string>("1");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const sidebarRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const isScrollingToPage = useRef(false);
  const visiblePages = useRef(new Set<number>());
  const [, setRenderTick] = useState(0);
  const modals = useModals();
  const { t } = useTranslation();
  const size = useDebouncedResize();

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

  function onDocumentLoadSuccess({
    numPages: nextNumPages,
  }: PDFDocumentProxy): void {
    setNumPages(nextNumPages);
    setCurrentPage(1);
    setPageInputValue("1");
  }

  const scrollToPage = useCallback((page: number) => {
    const container = containerRef.current;
    if (!container) return;
    const el = container.querySelector(`[data-page-number="${page}"]`);
    if (!el) return;
    isScrollingToPage.current = true;
    el.scrollIntoView({ behavior: "smooth", block: "start" });
    setTimeout(() => {
      isScrollingToPage.current = false;
    }, 600);
  }, []);

  const goToPreviousPage = useCallback(() => {
    setCurrentPage((prev) => {
      const newPage = Math.max(1, prev - 1);
      setPageInputValue(String(newPage));
      scrollToPage(newPage);
      return newPage;
    });
  }, [scrollToPage]);

  const goToNextPage = useCallback(() => {
    setCurrentPage((prev) => {
      const newPage = Math.min(numPages, prev + 1);
      setPageInputValue(String(newPage));
      scrollToPage(newPage);
      return newPage;
    });
  }, [numPages, scrollToPage]);

  const goToPage = useCallback(
    (page: number) => {
      const clamped = Math.max(1, Math.min(numPages, page));
      setCurrentPage(clamped);
      setPageInputValue(String(clamped));
      scrollToPage(clamped);
    },
    [numPages, scrollToPage],
  );

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
      { root: container, rootMargin: "100%" },
    );

    const wrappers = container.querySelectorAll("[data-page-number]");
    wrappers.forEach((el) => observer.observe(el));

    return () => observer.disconnect();
  }, [numPages, width]);

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
  }, [numPages, width]);

  useEffect(() => {
    if (!isSidebarOpen || !sidebarRef.current) return;
    const active = sidebarRef.current.querySelector(
      ".pdf-preview__thumbnail--active",
    );
    if (active) {
      active.scrollIntoView({ block: "nearest", behavior: "smooth" });
    }
  }, [currentPage, isSidebarOpen]);

  const handlePageInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setPageInputValue(e.target.value);
  };

  const handlePageInputSubmit = () => {
    const parsed = parseInt(pageInputValue, 10);
    if (isNaN(parsed)) {
      setPageInputValue(String(currentPage));
      return;
    }
    goToPage(parsed);
  };

  const handlePageInputKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      handlePageInputSubmit();
    }
  };

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
          <div className="pdf-preview__sidebar" ref={sidebarRef}>
            <Document file={file} options={options}>
              {Array.from({ length: numPages }, (_, i) => {
                const page = i + 1;
                return (
                  <button
                    key={page}
                    className={`pdf-preview__thumbnail${currentPage === page ? " pdf-preview__thumbnail--active" : ""}`}
                    onClick={() => goToPage(page)}
                    aria-label={`Go to page ${page}`}
                  >
                    <Thumbnail pageNumber={page} height={150} />
                    <span className="pdf-preview__thumbnail-number">
                      {page}
                    </span>
                  </button>
                );
              })}
            </Document>
          </div>
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
      <div className="pdf-preview__controls">
        <Button
          variant="tertiary"
          color="neutral"
          onClick={() => setIsSidebarOpen((prev) => !prev)}
          aria-label="Toggle sidebar"
        >
          <Icon name="view_sidebar" />
        </Button>
        <div className="controls-vertical-separator" />
        <div className="pdf-preview__page-nav">
          <Button
            variant="tertiary"
            color="neutral"
            onClick={goToPreviousPage}
            disabled={currentPage <= 1}
            aria-label="Previous page"
          >
            <Icon name="chevron_left" />
          </Button>
          <div className="pdf-preview__page-indicator">
            <input
              type="text"
              className="pdf-preview__page-input"
              value={pageInputValue}
              onChange={handlePageInputChange}
              onBlur={handlePageInputSubmit}
              onKeyDown={handlePageInputKeyDown}
              aria-label="Current page"
            />
            <span className="pdf-preview__page-total">/ {numPages}</span>
          </div>
          <Button
            variant="tertiary"
            color="neutral"
            onClick={goToNextPage}
            disabled={currentPage >= numPages}
            aria-label="Next page"
          >
            <Icon name="chevron_right" />
          </Button>
        </div>
      </div>
    </div>
  );
}
