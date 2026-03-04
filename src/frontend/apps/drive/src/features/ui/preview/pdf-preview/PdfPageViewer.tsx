import {
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
import { useDebouncedResize } from "./useDebouncedResize";
import { pdfOptions } from "./pdfOptions";

const PAGE_GAP = 16;
const BASE_WIDTH = 800;
const PAGE_MARGIN = 32;

export interface PdfPageViewerHandle {
  scrollToPage: (page: number) => void;
}

interface PdfPageViewerProps {
  file?: File | null;
  numPages: number;
  zoom: number;
  onDocumentLoadSuccess: (pdf: PDFDocumentProxy) => void;
  onCurrentPageChange: (page: number) => void;
  onClick: (e: React.MouseEvent<HTMLDivElement>) => void;
}


export function PdfPageViewer({
  file,
  numPages,
  zoom,
  onDocumentLoadSuccess,
  onCurrentPageChange,
  onClick,
  ref,
}: PdfPageViewerProps & { ref?: React.Ref<PdfPageViewerHandle> }) {
  const listRef = useRef<List>(null);
  const prevZoomRef = useRef(zoom);
  const [scrollTop, setScrollTop] = useState(0);
  const listHeightRef = useRef(0);

  const size = useDebouncedResize();

  const width = useMemo(() => {
    return BASE_WIDTH + PAGE_MARGIN > size.width
      ? size.width - PAGE_MARGIN
      : BASE_WIDTH;
  }, [size.width]);

  const pageHeight = width * 1.414;

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

  // When zoom, pageHeight or numPages change, row heights must be recalculated
  // because react-virtualized caches them internally.
  // On zoom change we also scale scrollTop proportionally so the user stays
  // on the same part of the document (e.g. 2x zoom → 2x scroll offset).
  useEffect(() => {
    listRef.current?.recomputeRowHeights();

    if (prevZoomRef.current !== zoom && listRef.current) {
      const ratio = zoom / prevZoomRef.current;
      const newScrollTop = Math.round(scrollTop * ratio);

      listRef.current.scrollToPosition(newScrollTop);
      prevZoomRef.current = zoom;
    }
  }, [zoom, pageHeight, numPages]);

  // Find which page contains the vertical center of the viewport by walking
  // cumulative row heights until we pass the midpoint.
  const currentPage = useMemo(() => {
    if (numPages === 0) return 1;

    const viewportCenter = scrollTop + listHeightRef.current / 2;

    let offset = 0;
    for (let i = 0; i < numPages; i++) {
      const h = rowHeightForIndex(i);
      if (offset + h > viewportCenter) {
        return i + 1;
      }
      offset += h;
    }

    return numPages;
  }, [scrollTop, numPages, rowHeightForIndex]);

  useEffect(() => {
    onCurrentPageChange(currentPage);
  }, [currentPage]);

  const scrollToPage = useCallback(
    (page: number) => {
      if (!listRef.current) return;

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
    ({
      scrollTop: st,
      clientHeight,
    }: {
      scrollTop: number;
      clientHeight: number;
    }) => {
      listHeightRef.current = clientHeight;
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
        options={pdfOptions}
        loading={loadingContainerSkeleton}
      >
        <AutoSizer>
          {({ height, width: autoWidth }) => {
            // When zoomed in the page content may exceed the viewport width.
            // The wrapper div is clamped to the viewport (autoWidth) and scrolls
            // horizontally, while the List itself is sized to the full content
            // width so pages render uncropped.
            const listWidth = Math.max(autoWidth, width * zoom);
            return (
              <div
                style={{
                  width: autoWidth,
                  height,
                }}
                className="pdf-preview__horizontal-scroll"
              >
                <List
                  ref={listRef}
                  height={height}
                  width={listWidth}
                  rowCount={numPages}
                  rowHeight={rowHeight}
                  overscanRowCount={3}
                  onScroll={handleScroll}
                  rowRenderer={rowRenderer}
                  style={{ outline: "none" }}
                />
              </div>
            );
          }}
        </AutoSizer>
      </Document>
    </div>
  );
}
