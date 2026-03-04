import {
  forwardRef,
  useCallback,
  useEffect,
  useImperativeHandle,
  useMemo,
  useRef,
  useState,
} from "react";
import { Document, Page } from "react-pdf";
import type { PDFDocumentProxy } from "pdfjs-dist";
import { AutoSizer, List } from "react-virtualized";
import type { ListRowRenderer, Index } from "react-virtualized";

const options = {
  cMapUrl: "/cmaps/",
  standardFontDataUrl: "/standard_fonts/",
  wasmUrl: "/wasm/",
  isEvalSupported: false,
};

const PAGE_GAP = 16;

export interface PdfPageViewerHandle {
  scrollToPage: (page: number) => void;
}

interface PdfPageViewerProps {
  file?: File | null;
  numPages: number;
  width: number;
  pageHeight: number;
  zoom: number;
  onDocumentLoadSuccess: (pdf: PDFDocumentProxy) => void;
  onCurrentPageChange: (page: number) => void;
  onClick: (e: React.MouseEvent<HTMLDivElement>) => void;
}

export const PdfPageViewer = forwardRef<
  PdfPageViewerHandle,
  PdfPageViewerProps
>(function PdfPageViewer(
  {
    file,
    numPages,
    width,
    pageHeight,
    zoom,
    onDocumentLoadSuccess,
    onCurrentPageChange,
    onClick,
  },
  ref,
) {
  const listRef = useRef<List>(null);
  const prevZoomRef = useRef(zoom);
  const [scrollTop, setScrollTop] = useState(0);
  const [listHeight, setListHeight] = useState(0);

  // When scrollToPage is called, the virtualizer scrolls to the target page
  // but currentPage (computed from viewport center) may briefly land on an
  // adjacent page, triggering a parent re-render that shifts scroll again,
  // causing an infinite loop. These refs lock the reported page to the
  // scroll target for 150ms while the virtualizer settles.
  const programmaticPageRef = useRef<number | null>(null);
  const programmaticTimerRef = useRef<ReturnType<typeof setTimeout>>(undefined);

  useEffect(() => {
    return () => clearTimeout(programmaticTimerRef.current);
  }, []);

  const rowHeightForIndex = useCallback(
    (index: number) => {
      const h = pageHeight * zoom;
      // No trailing gap on the last row
      if (index === numPages - 1) return h;
      return h + PAGE_GAP * zoom;
    },
    [pageHeight, zoom, numPages],
  );

  const rowHeight = useCallback(
    ({ index }: Index) => rowHeightForIndex(index),
    [rowHeightForIndex],
  );

  // Recompute row heights when zoom changes and preserve scroll position
  useEffect(() => {
    listRef.current?.recomputeRowHeights();

    if (prevZoomRef.current !== zoom && listRef.current) {
      const ratio = zoom / prevZoomRef.current;
      const newScrollTop = Math.round(scrollTop * ratio);

      clearTimeout(programmaticTimerRef.current);
      programmaticPageRef.current = currentPage;
      programmaticTimerRef.current = setTimeout(() => {
        programmaticPageRef.current = null;
      }, 150);

      listRef.current.scrollToPosition(newScrollTop);
      prevZoomRef.current = zoom;
    }
  }, [zoom, pageHeight, numPages]);

  const currentPage = useMemo(() => {
    if (numPages === 0) return 1;

    const viewportCenter = scrollTop + listHeight / 2;

    let offset = 0;
    for (let i = 0; i < numPages; i++) {
      const h = rowHeightForIndex(i);
      if (offset + h > viewportCenter) {
        return i + 1;
      }
      offset += h;
    }

    return numPages;
  }, [scrollTop, listHeight, numPages, rowHeightForIndex]);

  useEffect(() => {
    onCurrentPageChange(programmaticPageRef.current ?? currentPage);
  }, [currentPage]);

  const scrollToPage = useCallback(
    (page: number) => {
      if (!listRef.current) return;

      clearTimeout(programmaticTimerRef.current);
      programmaticPageRef.current = page;
      programmaticTimerRef.current = setTimeout(() => {
        programmaticPageRef.current = null;
      }, 150);

      // Compute offset for the target page
      let offset = 0;
      for (let i = 0; i < page - 1; i++) {
        offset += rowHeightForIndex(i);
      }
      listRef.current.scrollToPosition(offset);
    },
    [rowHeightForIndex],
  );

  useImperativeHandle(ref, () => ({ scrollToPage }), [scrollToPage]);

  const handleScroll = useCallback(
    ({ scrollTop: st }: { scrollTop: number }) => {
      setScrollTop(st);
    },
    [],
  );

  const rowRenderer: ListRowRenderer = ({ index, key, style }) => (
    <div
      key={key}
      style={{
        ...style,
        display: "flex",
        justifyContent: "center",
        paddingTop: PAGE_GAP * zoom,
        boxSizing: "border-box",
      }}
    >
      <Page
        pageNumber={index + 1}
        width={width}
        scale={zoom}
        loading={pageSkeleton}
      />
    </div>
  );

  const pageSkeleton = (
    <div
      className="pdf-preview__page-skeleton"
      style={{ height: pageHeight * zoom, width: width * zoom }}
    />
  );

  const loadingContainerSkeleton = (
    <div className="pdf-preview__container-skeleton">{pageSkeleton}</div>
  );

  if (!file) {
    return (
      <div className="pdf-preview__container">{loadingContainerSkeleton}</div>
    );
  }

  return (
    <div className="pdf-preview__container" onClick={onClick}>
      <Document
        file={file}
        onLoadSuccess={onDocumentLoadSuccess}
        options={options}
        loading={loadingContainerSkeleton}
      >
        <AutoSizer>
          {({ height, width: autoWidth }) => {
            // Track viewport height for currentPage calculation
            if (height !== listHeight) {
              // Use setTimeout to avoid setState during render
              setTimeout(() => setListHeight(height), 0);
            }
            return (
              <List
                ref={listRef}
                height={height}
                width={autoWidth}
                rowCount={numPages}
                rowHeight={rowHeight}
                overscanRowCount={3}
                onScroll={handleScroll}
                rowRenderer={rowRenderer}
                style={{ outline: "none" }}
              />
            );
          }}
        </AutoSizer>
      </Document>
    </div>
  );
});
