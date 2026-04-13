/**
 * Polyfills required by pdfjs-dist for older browsers (e.g. Edge)
 * that lack these newer APIs.
 *
 * They live in a dedicated file so they are imported as the very first
 * module in PreviewPdf.tsx — before react-pdf or pdfjs-dist execute —
 * guaranteeing the APIs exist when PDF code initialises.
 * A separate file also makes it easy to remove once browser support
 * catches up.
 */

if (
  typeof (URL as unknown as { parse?: unknown }).parse === "undefined"
) {
  (URL as unknown as Record<string, unknown>).parse = function (
    url: string,
    base?: string,
  ) {
    try {
      return new URL(url, base);
    } catch {
      return null;
    }
  };
}

if (typeof Promise.withResolvers === "undefined") {
  Promise.withResolvers = function <T>() {
    let resolve!: (value: T | PromiseLike<T>) => void;
    let reject!: (reason?: unknown) => void;
    const promise = new Promise<T>((res, rej) => {
      resolve = res;
      reject = rej;
    });
    return { promise, resolve, reject };
  };
}
