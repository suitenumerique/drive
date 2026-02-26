import { useEffect, useRef, useState } from "react";
import { Document, Page } from "react-pdf";
import type { PDFDocumentProxy } from "pdfjs-dist";

const options = {
  cMapUrl: "/cmaps/",
  standardFontDataUrl: "/standard_fonts/",
  wasmUrl: "/wasm/",
  isEvalSupported: false,
};

const PRELOAD_PAGES = 4;

interface PdfPageViewerProps {
  file?: File | null;
  numPages: number;
  width: number;
  pageHeight: number;
  zoom: number;
  containerRef: React.RefObject<HTMLDivElement | null>;
  onDocumentLoadSuccess: (pdf: PDFDocumentProxy) => void;
  onClick: (e: React.MouseEvent<HTMLDivElement>) => void;
}

export function PdfPageViewer({
  file,
  numPages,
  width,
  pageHeight,
  zoom,
  containerRef,
  onDocumentLoadSuccess,
  onClick,
}: PdfPageViewerProps) {
  const visiblePages = useRef(new Set<number>());
  const [, setRenderTick] = useState(0);
  const [docReady, setDocReady] = useState(false);

  const pageSkeleton = (
    <div
      className="pdf-preview__page-skeleton"
      style={{ height: pageHeight * zoom, width: width * zoom }}
    />
  );

  // Virtualization observer: track which pages are near the viewport
  useEffect(() => {
    const container = containerRef.current;
    if (!container || numPages <= 0 || !docReady) return;

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
      { root: container, rootMargin: `${PRELOAD_PAGES * pageHeight * zoom}px` },
    );

    const wrappers = container.querySelectorAll("[data-page-number]");
    wrappers.forEach((el) => observer.observe(el));

    return () => observer.disconnect();
  }, [numPages, width, pageHeight, zoom, containerRef, docReady]);

  if (!file) {
    return (
      <div className="pdf-preview__container" ref={containerRef}>
        <div className="pdf-preview__page-wrapper">
          <div
            className="pdf-preview__page-skeleton"
            style={{ height: pageHeight * zoom, width: width * zoom }}
          />
        </div>
      </div>
    );
  }

  return (
    <div className="pdf-preview__container" ref={containerRef}>
      <div className="pdf-preview__page-wrapper" onClick={onClick}>
        <Document
          file={file}
          onLoadSuccess={(pdf) => {
            setDocReady(true);
            onDocumentLoadSuccess(pdf);
          }}
          options={options}
          loading={pageSkeleton}
        >
          {Array.from({ length: numPages }, (_, i) => {
            const page = i + 1;
            const isVisible = visiblePages.current.has(page);
            return (
              <div
                key={page}
                data-page-number={page}
                // This is necessary to ensure the page is the correct height.
                // Setting width and height to <Page> is not enough, because during its initialization,
                // The height is not guaranteed to be correct. I see that for a few frames <Page> renders with a small
                // height, probably because it's still loading. But it makes the IntersectionObserver detect up to 5fth page
                // to be visible: when it happens uppon loading the current page in the input field is set to 5. But the
                // displayed page is still 1.
                // So by setting the height here, we ensure that the page is the correct height from the beginning.
                style={{ minHeight: pageHeight * zoom, width: width * zoom }}
              >
                {isVisible ? (
                  <Page
                    pageNumber={page}
                    width={width}
                    scale={zoom}
                    loading={pageSkeleton}
                  />
                ) : (
                  pageSkeleton
                )}
              </div>
            );
          })}
        </Document>
      </div>
    </div>
  );
}
