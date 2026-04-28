import { useCallback, useRef, useState } from "react";
import type { PDFDocumentProxy } from "pdfjs-dist";

export interface PageDimension {
  w: number;
  h: number;
}

// Shared ratio fallback for rows whose dimensions have not yet been fetched.
// Matches ISO 216 A4 portrait so first paint looks identical to the previous
// hardcoded layout until real dimensions arrive.
export const FALLBACK_RATIO = 1.414;

export type PageDimensionsMap = ReadonlyMap<number, PageDimension>;

export interface UsePdfPageDimensionsResult {
  pageDimensions: PageDimensionsMap;
  requestPageDimension: (page: number) => void;
  // Ensures dimensions for the given pages are loaded. Resolves with the
  // up-to-date pageDimensions map once every requested page is cached —
  // callers use the resolved map directly to compute offsets without waiting
  // for React to commit the state update. Pages already cached or in flight
  // dedupe with existing work.
  ensurePageDimensions: (pages: number[]) => Promise<PageDimensionsMap>;
  setPdf: (pdf: PDFDocumentProxy | null) => void;
}

// Lazy per-page viewport cache. Consumers call requestPageDimension(page) when
// a page scrolls into virtualization overscan; the returned pageDimensions map
// is the read side of the cache. Once the page's dimensions are fetched, they
// become available via pageDimensions, triggering a re-render of the PDF
// previews with the correct dimension.
export function usePdfPageDimensions(): UsePdfPageDimensionsResult {
  const pdfRef = useRef<PDFDocumentProxy | null>(null);
  // Tracks fetches currently in progress so concurrent callers share one
  // getPage() round trip. Two distinct jobs:
  //   - Dedup: onRowsRendered fires on every scroll tick, so the same page
  //     can be requested many times before the first fetch resolves.
  //   - Synchronisation: ensurePageDimensions([1..N]) (used by scrollToPage)
  //     awaits Promise.all of fetchPageDimension(i). If another caller (e.g.
  //     the overscan prefetch) has already started a fetch for page i, we
  //     must return *that* Promise — otherwise `await` would resolve before
  //     the stored fetch's .then() commits dimensions to pageDimensionsRef,
  //     and scrollToPage would read stale dimensions when computing its
  //     offset.
  const inFlightRef = useRef<Map<number, Promise<void>>>(new Map());
  // Mirror of pageDimensions state, read synchronously inside
  // requestPageDimension to dedupe fetches without stale-closure reads of
  // state.
  const pageDimensionsRef = useRef<Map<number, PageDimension>>(new Map());
  const [pageDimensions, setPageDimensions] = useState<
    Map<number, PageDimension>
  >(() => new Map());

  const setPdf = useCallback((pdf: PDFDocumentProxy | null) => {
    // Any cached dimensions belong to the previous document; reset on every
    // switch (including clear) so stale heights don't leak into the new doc.
    pdfRef.current = pdf;
    inFlightRef.current = new Map();
    pageDimensionsRef.current = new Map();
    setPageDimensions(new Map());
  }, []);

  const fetchPageDimension = useCallback((page: number): Promise<void> => {
    const pdf = pdfRef.current;
    if (!pdf) {
      return Promise.resolve();
    }
    if (pageDimensionsRef.current.has(page)) {
      return Promise.resolve();
    }
    const existing = inFlightRef.current.get(page);
    if (existing) {
      return existing;
    }

    const promise = pdf
      .getPage(page)
      .then((p) => {
        const vp = p.getViewport({ scale: 1 });
        const next = new Map(pageDimensionsRef.current);
        next.set(page, { w: vp.width, h: vp.height });
        pageDimensionsRef.current = next;
        setPageDimensions(next);
      })
      .catch((err) => {
        // Resolve (don't reject) on failure so ensurePageDimensions stays
        // usable: a page-input jump still scrolls, with FALLBACK_RATIO
        // standing in for the failed page via getRatio's map miss.
        console.warn(`Failed to fetch dimensions for PDF page ${page}`, err);
      })
      .finally(() => {
        inFlightRef.current.delete(page);
      });
    inFlightRef.current.set(page, promise);
    return promise;
  }, []);

  const requestPageDimension = useCallback(
    (page: number) => {
      void fetchPageDimension(page);
    },
    [fetchPageDimension],
  );

  const ensurePageDimensions = useCallback(
    async (pages: number[]): Promise<PageDimensionsMap> => {
      await Promise.all(pages.map((p) => fetchPageDimension(p)));
      return pageDimensionsRef.current;
    },
    [fetchPageDimension],
  );

  return {
    pageDimensions,
    requestPageDimension,
    ensurePageDimensions,
    setPdf,
  };
}
