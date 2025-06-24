import { useState, useRef, useCallback, useEffect } from "react";
import { Document, Page } from "react-pdf";

import { pdfjs } from "react-pdf";

pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;

interface PreviewPdfProps {
  src?: string;
}

export const PreviewPdf = ({ src }: PreviewPdfProps) => {
  return (
    <iframe
      src={src}
      width="100%"
      height="100%"
      className="pdf-container__object"
    >
      <p>
        Alternative text - include a link <a href="myfile.pdf">to the PDF!</a>
      </p>
    </iframe>
  );
};

export const PreviewPdf2: React.FC<PreviewPdfProps> = ({
  src = "http://localhost:3000/pdf/test.pdf",
}) => {
  const [numPages, setNumPages] = useState<number>();
  const [scale, setScale] = useState<number>(1.0);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [targetPage, setTargetPage] = useState<string>("");
  const containerRef = useRef<HTMLDivElement>(null);

  // Handle document load success
  const onDocumentLoadSuccess = useCallback(
    ({ numPages }: { numPages: number }): void => {
      setNumPages(numPages);
      setIsLoading(false);
    },
    []
  );

  // Handle document load error
  const onDocumentLoadError = useCallback((error: Error): void => {
    console.error("Error loading PDF:", error);
    setIsLoading(false);
  }, []);

  // Navigate to specific page
  const goToPage = useCallback(
    (pageNumber: number) => {
      if (pageNumber >= 1 && pageNumber <= (numPages || 1)) {
        // Find the page element and scroll to it
        const pageElement = document.querySelector(
          `[data-page="${pageNumber}"]`
        );
        console.log(pageElement);
        if (pageElement && containerRef.current) {
          // Calculate the position of the page element relative to the pdf-content container
          const pageTop = (pageElement as HTMLElement).offsetTop;
          const containerTop = containerRef.current.offsetTop;
          const scrollTop = pageTop - containerTop - 20; // Adjust for padding

          // Scroll the pdf-content container to the calculated position
          containerRef.current.scrollTop = scrollTop;
        }
        setTargetPage("");
      }
    },
    [numPages]
  );

  // Handle page input change
  const handlePageInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const value = e.target.value;
      // Only allow numbers
      if (value === "" || /^\d+$/.test(value)) {
        setTargetPage(value);
      }
    },
    []
  );

  // Handle page input submit
  const handlePageInputSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      const pageNumber = parseInt(targetPage);
      if (pageNumber) {
        goToPage(pageNumber);
      }
    },
    [targetPage, goToPage]
  );

  // Zoom in
  const zoomIn = useCallback(() => {
    setScale((prev) => Math.min(prev + 0.25, 3.0));
  }, []);

  // Zoom out
  const zoomOut = useCallback(() => {
    setScale((prev) => Math.max(prev - 0.25, 0.5));
  }, []);

  // Reset zoom
  const resetZoom = useCallback(() => {
    setScale(1.0);
  }, []);

  // Handle keyboard navigation
  const handleKeyDown = useCallback(
    (event: KeyboardEvent) => {
      switch (event.key) {
        case "+":
        case "=":
          event.preventDefault();
          zoomIn();
          break;
        case "-":
          event.preventDefault();
          zoomOut();
          break;
        case "0":
          event.preventDefault();
          resetZoom();
          break;
      }
    },
    [zoomIn, zoomOut, resetZoom]
  );

  // Add keyboard event listener
  useEffect(() => {
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [handleKeyDown]);

  // Render all pages
  const renderPages = () => {
    const pages = [];
    for (let i = 1; i <= (numPages || 0); i++) {
      pages.push(
        <div key={i} className="pdf-page-wrapper" data-page={i}>
          <Page
            pageNumber={i}
            scale={scale}
            renderTextLayer={false}
            renderAnnotationLayer={false}
          />
        </div>
      );
    }
    return pages;
  };

  return (
    <div className="pdf-preview-container">
      {/* Toolbar */}
      <div className="toolbar">
        {/* Page info and navigation */}
        <div className="page-navigation">
          <div className="page-info">
            {numPages ? `${numPages} page${numPages > 1 ? "s" : ""}` : "..."}
          </div>

          <form onSubmit={handlePageInputSubmit} className="page-input-form">
            <input
              type="text"
              value={targetPage}
              onChange={handlePageInputChange}
              placeholder="Page..."
              className="page-input"
              maxLength={3}
            />
            <button
              type="submit"
              className="go-to-page-button"
              disabled={
                !targetPage ||
                parseInt(targetPage) < 1 ||
                parseInt(targetPage) > (numPages || 1)
              }
            >
              Aller
            </button>
          </form>
        </div>

        {/* Zoom controls */}
        <div className="zoom-controls">
          <button
            className="zoom-button"
            onClick={zoomOut}
            disabled={scale <= 0.5}
          >
            🔍-
          </button>

          <span className="zoom-level">{Math.round(scale * 100)}%</span>

          <button
            className="zoom-button"
            onClick={zoomIn}
            disabled={scale >= 3.0}
          >
            🔍+
          </button>

          <button className="reset-button" onClick={resetZoom}>
            Reset
          </button>
        </div>

        {/* Keyboard shortcuts info */}
        <div className="keyboard-shortcuts">
          Raccourcis: +/- (zoom), 0 (reset)
        </div>
      </div>

      {/* PDF content with scroll */}
      <div ref={containerRef} className="pdf-content">
        {isLoading && (
          <div className="loading-container">Chargement du PDF...</div>
        )}

        <Document
          file={src}
          onLoadSuccess={onDocumentLoadSuccess}
          onLoadError={onDocumentLoadError}
          loading={
            <div className="loading-container">Chargement du PDF...</div>
          }
          error={
            <div className="error-container">
              Erreur lors du chargement du PDF
            </div>
          }
        >
          <div className="pdf-pages-container">{renderPages()}</div>
        </Document>
      </div>
    </div>
  );
};
