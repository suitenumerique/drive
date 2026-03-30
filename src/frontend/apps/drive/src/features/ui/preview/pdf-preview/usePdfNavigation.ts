import { useCallback, useEffect, useRef, useState } from "react";
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

  // onItemClick handles internal PDF links (e.g. table of contents entries).
  // It is called by react-pdf's Document via a viewer ref that is created once
  // with useRef, so the callback is captured in a stale closure from the first
  // render. We use a ref to always access the latest goToPage (which depends
  // on numPages) so navigation targets the correct page.
  //
  // onClick (handlePdfClick) handles regular DOM clicks on the annotation layer
  // — it intercepts external links to show a redirect disclaimer modal.
  const goToPageRef = useRef(goToPage);
  useEffect(() => {
    goToPageRef.current = goToPage;
  }, [goToPage]);

  const onItemClick = useCallback((args: { pageNumber: number }) => {
    goToPageRef.current(args.pageNumber);
  }, []);

  return {
    goToPage,
    onDocumentLoadSuccess,
    pageInputValue,
    setPageInputValue,
    handlePageInputChange,
    handlePageInputSubmit,
    handlePageInputKeyDown,
    onItemClick,
  };
};
