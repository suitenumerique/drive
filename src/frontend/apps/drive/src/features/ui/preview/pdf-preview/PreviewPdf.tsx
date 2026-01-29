import { useCallback, useEffect, useState } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import type { PDFDocumentProxy } from 'pdfjs-dist';
import { Button, useModals } from '@openfun/cunningham-react';
import { Icon } from '@gouvfr-lasuite/ui-kit';
import { useTranslation } from 'react-i18next';
import 'react-pdf/dist/Page/AnnotationLayer.css';
import 'react-pdf/dist/Page/TextLayer.css';

pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;

const options = {
  cMapUrl: '/cmaps/',
  standardFontDataUrl: '/standard_fonts/',
  wasmUrl: '/wasm/',
  isEvalSupported: false,
};

const BASE_WIDTH = 800;
const ZOOM_STEP = 0.25;
const MIN_ZOOM = 0.5;
const MAX_ZOOM = 2;


function debounce<T extends (...args: any[]) => any>(
  func: T,
  timeout = 300
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
  const [zoom, setZoom] = useState<number>(1);
  const [pageInputValue, setPageInputValue] = useState<string>('1');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const modals = useModals();
  const { t } = useTranslation();
  const size = useDebouncedResize();

  const getWidth = () => {
    if (size.width < BASE_WIDTH) {
      return size.width;
    }
    return BASE_WIDTH;
  }

  
  const [width, setWidth] = useState(getWidth());
  useEffect(() => {
    setWidth(getWidth());
  }, [size.width]);

  useEffect(() => {
    const fetchPdf = async () => {
      setIsLoading(true);
      setError(null);

      try {
        const response = await fetch(src, { credentials: 'include' });

        if (!response.ok) {
          throw new Error(`Failed to fetch PDF: ${response.status}`);
        }

        const blob = await response.blob();
        const filename = src.split('/').pop() || 'document.pdf';
        const pdfFile = new File([blob], filename, { type: 'application/pdf' });

        setFile(pdfFile);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load PDF');
      } finally {
        setIsLoading(false);
      }
    };

    fetchPdf();
  }, [src]);

  function onDocumentLoadSuccess({ numPages: nextNumPages }: PDFDocumentProxy): void {
    setNumPages(nextNumPages);
    setCurrentPage(1);
    setPageInputValue('1');
  }

  const goToPreviousPage = useCallback(() => {
    setCurrentPage((prev) => {
      const newPage = Math.max(1, prev - 1);
      setPageInputValue(String(newPage));
      return newPage;
    });
  }, []);

  const goToNextPage = useCallback(() => {
    setCurrentPage((prev) => {
      const newPage = Math.min(numPages, prev + 1);
      setPageInputValue(String(newPage));
      return newPage;
    });
  }, [numPages]);

  const handlePageInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setPageInputValue(e.target.value);
  };

  const handlePageInputSubmit = () => {
    const parsed = parseInt(pageInputValue, 10);
    if (isNaN(parsed)) {
      setPageInputValue(String(currentPage));
      return;
    }
    const clamped = Math.max(1, Math.min(numPages, parsed));
    setCurrentPage(clamped);
    setPageInputValue(String(clamped));
  };

  const handlePageInputKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      handlePageInputSubmit();
    }
  };

  const zoomIn = useCallback(() => {
    setZoom((prev) => Math.min(MAX_ZOOM, prev + ZOOM_STEP));
  }, []);

  const zoomOut = useCallback(() => {
    setZoom((prev) => Math.max(MIN_ZOOM, prev - ZOOM_STEP));
  }, []);

  const resetZoom = useCallback(() => {
    setZoom(1);
  }, []);

  const handlePdfClick = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    const target = e.target as HTMLElement;
    const anchor = target.closest('a');

    if (anchor && anchor.href) {
      e.preventDefault();
      e.stopPropagation();

      modals.confirmationModal({
        title: t('file_preview.external_link.title'),
        children: (<div>
          <p>{t('file_preview.external_link.description')}</p>
          <pre className="pdf-preview__external-link">{anchor.href}</pre>
          <p>{t('file_preview.external_link.confirm_question')}</p>
        </div>),
        onDecide: (decision) => {
          if (decision === 'yes') {
            window.open(anchor.href, '_blank', 'noopener,noreferrer');
          }
        },
      });
    }
  }, [modals, t]);

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
      <div className="pdf-preview__container">
        <div
          className="pdf-preview__page-wrapper"
          style={{ transform: `scale(${zoom})` }}
          onClick={handlePdfClick}
        >
          <Document file={file} onLoadSuccess={onDocumentLoadSuccess} options={options}>
            <Page
              pageNumber={currentPage}
              width={width}
            />
          </Document>
        </div>
      </div>
      <div className="pdf-preview__controls">
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
        <div className="controls-vertical-separator" />
        <div className="zoom-control">
          <Button
            variant="tertiary"
            color="neutral"
            onClick={zoomOut}
            disabled={zoom <= MIN_ZOOM}
            aria-label="Zoom out"
          >
            <Icon name="zoom_out" />
          </Button>
          <div
            className="zoom-control__value"
            role="button"
            onClick={resetZoom}
            tabIndex={0}
            onKeyDown={(e) => e.key === 'Enter' && resetZoom()}
          >
            {Math.round(zoom * 100)}%
          </div>
          <Button
            variant="tertiary"
            color="neutral"
            onClick={zoomIn}
            disabled={zoom >= MAX_ZOOM}
            aria-label="Zoom in"
          >
            <Icon name="zoom_in" />
          </Button>
        </div>
      </div>
    </div>
  );
}
