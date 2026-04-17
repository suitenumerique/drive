/**
 * Open the browser print dialog for an image without navigating away.
 *
 * The image is loaded inside a hidden same-origin iframe built with `srcdoc`
 * (not `src`) so we can call `contentWindow.print()` from the parent without
 * running into the cross-origin restriction that would apply if the iframe's
 * document came from the image URL's origin.
 */
export const printImage = (imageUrl: string): void => {
  const iframe = document.createElement("iframe");
  iframe.setAttribute("aria-hidden", "true");
  iframe.style.cssText =
    "position:fixed;right:0;bottom:0;width:0;height:0;border:0;";
  iframe.srcdoc = `<!DOCTYPE html><html><head><style>
      @page { margin: 0; }
      html, body { margin: 0; padding: 0; }
      img { max-width: 100%; max-height: 100vh; display: block; margin: auto; }
    </style></head><body><img src="${imageUrl}" alt="" /></body></html>`;

  iframe.onload = () => {
    const img = iframe.contentDocument?.querySelector("img");
    const triggerPrint = () => {
      iframe.contentWindow?.focus();
      iframe.contentWindow?.print();
    };
    iframe.contentWindow?.addEventListener(
      "afterprint",
      () => iframe.remove(),
      { once: true },
    );
    if (img && !img.complete) {
      img.addEventListener("load", triggerPrint, { once: true });
      img.addEventListener("error", () => iframe.remove(), { once: true });
    } else {
      triggerPrint();
    }
  };

  document.body.appendChild(iframe);
};
