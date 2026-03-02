import { useEffect, useRef, useState } from "react";
import { Document, Thumbnail } from "react-pdf";

const options = {
  cMapUrl: "/cmaps/",
  standardFontDataUrl: "/standard_fonts/",
  wasmUrl: "/wasm/",
  isEvalSupported: false,
};

interface PdfThumbnailSidebarProps {
  file?: File | null;
  numPages: number;
  currentPage: number;
  goToPage: (page: number) => void;
  isOpen: boolean;
}

const TRANSITION_DELAY = 300;

// Two-phase mount/unmount to allow CSS transitions to play out:
// Opening: mount immediately (unmount=false), then defer isOpenProxy=true
//   so the DOM is present before the "open" class triggers the transition.
// Closing: remove the "open" class first (isOpenProxy=false), wait for the
//   transition to finish (TRANSITION_DELAY), then unmount the component.
// When closed the component is not mounted, which is better for performance
// as this component is quite heavy and is not needed when closed.
export function PdfThumbnailSidebar(props: PdfThumbnailSidebarProps) {
  const [unmount, setUnmount] = useState(true);
  const [isOpenProxy, setIsOpenProxy] = useState(props.isOpen);

  useEffect(() => {
    if (props.isOpen) {
      setUnmount(false);
      setTimeout(() => setIsOpenProxy(true), 100);
    } else {
      setIsOpenProxy(false);
      // The 1.1 is to allow for the transition to finish.
      // It is a safety margin to avoid the component being unmounted too early.
      setTimeout(() => setUnmount(true), TRANSITION_DELAY * 1.1);
    }
  }, [props.isOpen]);

  if (unmount) {
    return null;
  }

  return <PdfThumbnailSidebarContent {...props} isOpen={isOpenProxy} />;
}

export function PdfThumbnailSidebarContent({
  file,
  numPages,
  currentPage,
  goToPage,
  isOpen,
}: PdfThumbnailSidebarProps) {
  const sidebarRef = useRef<HTMLDivElement>(null);
  const visibleThumbnails = useRef(new Set<number>());
  const [, setRenderTick] = useState(0);
  const [docReady, setDocReady] = useState(false);

  // Thumbnail virtualization observer
  useEffect(() => {
    const sidebar = sidebarRef.current;
    if (!sidebar || numPages <= 0 || !docReady) return;

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
  }, [numPages, docReady]);

  // Auto-scroll active thumbnail into view
  useEffect(() => {
    if (!sidebarRef.current) return;
    const active = sidebarRef.current.querySelector(
      ".pdf-preview__thumbnail--active",
    );
    if (active) {
      active.scrollIntoView({ block: "nearest", behavior: "smooth" });
    }
  }, [currentPage]);

  if (!file) {
    return (
      <div
        className={`pdf-preview__sidebar${!isOpen ? " pdf-preview__sidebar--closed" : ""}`}
        ref={sidebarRef}
      >
        <div className="pdf-preview__thumbnail-skeleton" />
      </div>
    );
  }

  return (
    <div
      className={`pdf-preview__sidebar${!isOpen ? " pdf-preview__sidebar--closed" : ""}`}
      ref={sidebarRef}
    >
      <Document
        file={file}
        options={options}
        onLoadSuccess={() => setDocReady(true)}
        loading={<div className="pdf-preview__thumbnail-skeleton" />}
        // Thumbnails may contain clickable internal links (e.g., table of contents).
        // Without onItemClick, react-pdf cannot resolve those links since only
        // thumbnails are rendered here, not full pages. We intercept the click
        // and navigate the main viewer instead.
        onItemClick={({ pageNumber }) => goToPage(pageNumber)}
      >
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
              {visibleThumbnails.current.has(page) ? (
                <Thumbnail
                  pageNumber={page}
                  height={150}
                  loading={<div className="pdf-preview__thumbnail-skeleton" />}
                />
              ) : (
                <div className="pdf-preview__thumbnail-skeleton" />
              )}
              <span className="pdf-preview__thumbnail-number">{page}</span>
            </button>
          );
        })}
      </Document>
    </div>
  );
}
