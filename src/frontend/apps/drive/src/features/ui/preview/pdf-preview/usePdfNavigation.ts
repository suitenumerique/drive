import { useCallback, useEffect, useRef, useState } from "react";
import type { PDFDocumentProxy } from "pdfjs-dist";

interface UsePdfNavigationParams {
  numPages: number;
  width: number;
  containerRef: React.RefObject<HTMLDivElement | null>;
}

export const usePdfNavigation = ({
  numPages,
  width,
  containerRef,
}: UsePdfNavigationParams) => {
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [pageInputValue, setPageInputValue] = useState<string>("1");
  const isScrollingToPage = useRef(false);

  const scrollToPage = useCallback(
    (page: number) => {
      const container = containerRef.current;
      if (!container) return;
      const el = container.querySelector(`[data-page-number="${page}"]`);
      if (!el) return;
      isScrollingToPage.current = true;
      el.scrollIntoView({ behavior: "smooth", block: "start" });
      setTimeout(() => {
        isScrollingToPage.current = false;
      }, 600);
    },
    [containerRef],
  );

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

  const onDocumentLoadSuccess = useCallback(
    ({ numPages: nextNumPages }: PDFDocumentProxy) => {
      setCurrentPage(1);
      setPageInputValue("1");
      return nextNumPages;
    },
    [],
  );

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

  // Current page tracking observer: updates currentPage on scroll
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
  }, [numPages, width, containerRef]);

  return {
    currentPage,
    scrollToPage,
    goToPreviousPage,
    goToNextPage,
    goToPage,
    onDocumentLoadSuccess,
    pageInputValue,
    handlePageInputChange,
    handlePageInputSubmit,
    handlePageInputKeyDown,
  };
};
