import { useCallback, useState } from "react";
import type { PDFDocumentProxy } from "pdfjs-dist";

interface UsePdfNavigationParams {
  numPages: number;
  currentPage: number;
  scrollToPage: (page: number) => void;
}

export const usePdfNavigation = ({
  numPages,
  currentPage,
  scrollToPage,
}: UsePdfNavigationParams) => {
  const [pageInputValue, setPageInputValue] = useState<string>("1");

  const goToPreviousPage = useCallback(() => {
    const newPage = Math.max(1, currentPage - 1);
    setPageInputValue(String(newPage));
    scrollToPage(newPage);
  }, [currentPage, scrollToPage]);

  const goToNextPage = useCallback(() => {
    const newPage = Math.min(numPages, currentPage + 1);
    setPageInputValue(String(newPage));
    scrollToPage(newPage);
  }, [numPages, currentPage, scrollToPage]);

  const goToPage = useCallback(
    (page: number) => {
      const clamped = Math.max(1, Math.min(numPages, page));
      setPageInputValue(String(clamped));
      scrollToPage(clamped);
    },
    [numPages, scrollToPage],
  );

  const onDocumentLoadSuccess = useCallback(
    ({ numPages: nextNumPages }: PDFDocumentProxy) => {
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

  return {
    goToPreviousPage,
    goToNextPage,
    goToPage,
    onDocumentLoadSuccess,
    pageInputValue,
    setPageInputValue,
    handlePageInputChange,
    handlePageInputSubmit,
    handlePageInputKeyDown,
  };
};
