import { useMemo, useState, useEffect } from "react";
import { Document, Page } from "react-pdf";
import { pdfjs } from "react-pdf";
import "react-pdf/dist/Page/AnnotationLayer.css";
import "react-pdf/dist/Page/TextLayer.css";
import { ZoomControl } from "../image-viewer/ImageViewer";

import { TransformWrapper, TransformComponent } from "react-zoom-pan-pinch";
import { useResponsive } from "@gouvfr-lasuite/ui-kit";
pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;

type PreviewPdfProps = {
  src: string;
};

export default function PreviewPdf({ src }: PreviewPdfProps) {
  const [numPages, setNumPages] = useState<number>();
  const { isMobile } = useResponsive();
  const options = useMemo(
    () => ({
      withCredentials: true,
      enableScripting: false,
      disableForms: true,
      disableAutoFetch: true,
      // disableFontFace: true,
    }),
    []
  );
  const [scale, setScale] = useState<number>(1);
  const [pageWidth, setPageWidth] = useState<number>(800);
  const [exceedsViewport, setExceedsViewport] = useState<boolean>(false);

  useEffect(() => {
    // Calculate page width based on container
    const updatePageWidth = () => {
      if (isMobile) {
        // On mobile, use full width minus padding
        const mobilePadding = 40;
        const availableWidth =
          typeof window !== "undefined"
            ? window.innerWidth - mobilePadding
            : 800;
        setPageWidth(availableWidth);
      } else {
        const maxWidth = 800;
        const containerPadding = 80;
        const availableWidth =
          typeof window !== "undefined"
            ? Math.min(maxWidth, window.innerWidth - containerPadding)
            : maxWidth;
        setPageWidth(availableWidth);
      }
    };

    updatePageWidth();
    window.addEventListener("resize", updatePageWidth);
    return () => window.removeEventListener("resize", updatePageWidth);
  }, [isMobile]);

  useEffect(() => {
    // Check if PDF width exceeds viewport width
    const checkViewportWidth = () => {
      if (typeof window !== "undefined") {
        const viewportWidth = window.innerWidth;
        const pdfWidth = pageWidth * scale;
        setExceedsViewport(pdfWidth > viewportWidth);
      }
    };

    checkViewportWidth();
    window.addEventListener("resize", checkViewportWidth);
    return () => window.removeEventListener("resize", checkViewportWidth);
  }, [pageWidth, scale]);

  function onDocumentLoadSuccess({ numPages }: { numPages: number }): void {
    setNumPages(numPages);
  }

  console.log("isMobile", isMobile);

  const pdfContent = (
    <Document
      options={options}
      file={src}
      onLoadSuccess={onDocumentLoadSuccess}
      loading={
        <div className="pdf-container__loading">Chargement du PDF...</div>
      }
    >
      {numPages &&
        Array.from(new Array(numPages), (el, index) => (
          <div
            key={`page_${index + 1}`}
            className="pdf-container__page-wrapper"
          >
            <Page
              scale={isMobile ? 1 : scale}
              width={pageWidth}
              pageNumber={index + 1}
              renderTextLayer={true}
              renderAnnotationLayer={true}
            />
          </div>
        ))}
    </Document>
  );

  if (isMobile) {
    return (
      <div className="pdf-container pdf-container--mobile">
        <TransformWrapper
          initialScale={1}
          minScale={0.5}
          maxScale={3}
          limitToBounds={true}
          centerOnInit={true}
          wheel={{ step: 0.1 }}
          pinch={{ step: 10 }}
          doubleClick={{ disabled: true }}
        >
          <TransformComponent
            wrapperClass="pdf-container__transform-wrapper"
            contentClass="pdf-container__transform-content"
          >
            <div className="pdf-container__scrollable pdf-container__scrollable--mobile">
              {pdfContent}
            </div>
          </TransformComponent>
        </TransformWrapper>
      </div>
    );
  }

  return (
    <div className="pdf-container">
      <div
        className={`pdf-container__scrollable ${
          exceedsViewport ? "pdf-container__scrollable--exceeds-viewport" : ""
        }`}
      >
        {pdfContent}
      </div>
      <div className="image-viewer__controls">
        <ZoomControl
          zoomOut={() => setScale(scale - 0.1)}
          zoomIn={() => setScale(scale + 0.1)}
          zoom={scale}
          resetView={() => setScale(1)}
        />
      </div>
    </div>
  );
}
