import { Document, Page } from "react-pdf";
import type { PDFDocumentProxy } from "pdfjs-dist";
import type { VirtualItem } from "@tanstack/react-virtual";

const options = {
  cMapUrl: "/cmaps/",
  standardFontDataUrl: "/standard_fonts/",
  wasmUrl: "/wasm/",
  isEvalSupported: false,
};

interface PdfPageViewerProps {
  file?: File | null;
  width: number;
  pageHeight: number;
  zoom: number;
  containerRef: React.RefObject<HTMLDivElement | null>;
  totalSize: number;
  virtualItems: VirtualItem[];
  onDocumentLoadSuccess: (pdf: PDFDocumentProxy) => void;
  onClick: (e: React.MouseEvent<HTMLDivElement>) => void;
}

export function PdfPageViewer({
  file,
  width,
  pageHeight,
  zoom,
  containerRef,
  totalSize,
  virtualItems,
  onDocumentLoadSuccess,
  onClick,
}: PdfPageViewerProps) {
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
          <div style={{ width: width * zoom, height: totalSize, position: "relative" }}>
            {virtualItems.map((virtualItem) => (
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
}
