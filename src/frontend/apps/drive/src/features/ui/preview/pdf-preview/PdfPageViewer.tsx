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
  file: File;
  numPages: number;
  width: number;
  pageHeight: number;
  containerRef: React.RefObject<HTMLDivElement | null>;
  onDocumentLoadSuccess: (pdf: PDFDocumentProxy) => void;
  onClick: (e: React.MouseEvent<HTMLDivElement>) => void;
}

export function PdfPageViewer({
  file,
  numPages,
  width,
  pageHeight,
  containerRef,
  onDocumentLoadSuccess,
  onClick,
}: PdfPageViewerProps) {
  const visiblePages = useRef(new Set<number>());
  const [, setRenderTick] = useState(0);

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
  }, [numPages, width, pageHeight, containerRef]);

  return (
    <div className="pdf-preview__container" ref={containerRef}>
      <div className="pdf-preview__page-wrapper" onClick={onClick}>
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
  );
}
