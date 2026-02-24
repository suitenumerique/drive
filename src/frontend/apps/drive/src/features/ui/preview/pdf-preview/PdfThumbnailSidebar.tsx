import { Document, Thumbnail } from "react-pdf";

const options = {
  cMapUrl: "/cmaps/",
  standardFontDataUrl: "/standard_fonts/",
  wasmUrl: "/wasm/",
  isEvalSupported: false,
};

interface PdfThumbnailSidebarProps {
  file: File;
  numPages: number;
  currentPage: number;
  visibleThumbnails: Set<number>;
  goToPage: (page: number) => void;
  sidebarRef: React.RefObject<HTMLDivElement | null>;
}

export function PdfThumbnailSidebar({
  file,
  numPages,
  currentPage,
  visibleThumbnails,
  goToPage,
  sidebarRef,
}: PdfThumbnailSidebarProps) {
  return (
    <div className="pdf-preview__sidebar" ref={sidebarRef}>
      <Document file={file} options={options}>
        {Array.from({ length: numPages }, (_, i) => {
          const page = i + 1;
          return (
            <button
              key={page}
              data-thumb-page={page}
              style={{ minHeight: 178 }}
              className={`pdf-preview__thumbnail${currentPage === page ? " pdf-preview__thumbnail--active" : ""}`}
              onClick={() => goToPage(page)}
              aria-label={`Go to page ${page}`}
            >
              {visibleThumbnails.has(page) && (
                <Thumbnail pageNumber={page} height={150} />
              )}
              <span className="pdf-preview__thumbnail-number">{page}</span>
            </button>
          );
        })}
      </Document>
    </div>
  );
}
